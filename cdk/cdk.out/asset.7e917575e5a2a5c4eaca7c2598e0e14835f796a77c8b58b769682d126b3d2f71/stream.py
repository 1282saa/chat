"""
WebSocket 실시간 스트리밍 Lambda 함수
"""
import json
import os
import boto3
import traceback
from datetime import datetime, timezone

# AWS 클라이언트
bedrock_client = boto3.client("bedrock-runtime")
dynamodb_client = boto3.client("dynamodb")
dynamodb_resource = boto3.resource("dynamodb")
apigateway_client = boto3.client("apigatewaymanagementapi")

# 환경 변수
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE')
PROMPT_META_TABLE = os.environ.get('PROMPT_META_TABLE')
PROMPT_BUCKET = os.environ.get('PROMPT_BUCKET')
CONVERSATIONS_TABLE = os.environ.get('CONVERSATIONS_TABLE', 'Conversations')
MESSAGES_TABLE = os.environ.get('MESSAGES_TABLE', 'Messages')
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

# DynamoDB tables
conversations_table = dynamodb_resource.Table(CONVERSATIONS_TABLE)
messages_table = dynamodb_resource.Table(MESSAGES_TABLE)

def handler(event, context):
    """
    WebSocket 스트리밍 메시지 처리
    """
    try:
        connection_id = event['requestContext']['connectionId']
        domain_name = event['requestContext']['domainName']
        stage = event['requestContext']['stage']
        
        # API Gateway Management API 클라이언트 설정
        endpoint_url = f"https://{domain_name}/{stage}"
        global apigateway_client
        apigateway_client = boto3.client(
            'apigatewaymanagementapi',
            endpoint_url=endpoint_url
        )
        
        # 요청 본문 파싱
        body = json.loads(event.get('body', '{}'))
        action = body.get('action')
        
        if action == 'stream':
            return handle_stream_request(connection_id, body)
        else:
            return send_error(connection_id, "지원하지 않는 액션입니다")
            
    except Exception as e:
        print(f"WebSocket 처리 오류: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def handle_stream_request(connection_id, data):
    """
    실시간 스트리밍 요청 처리
    """
    try:
        project_id = data.get('projectId')
        user_input = data.get('userInput')
        chat_history = data.get('chat_history', [])
        prompt_cards = data.get('prompt_cards', [])
        conversation_id = data.get('conversationId')  # New field for conversation tracking
        user_sub = data.get('userSub')  # User ID from frontend
        
        if not project_id or not user_input:
            return send_error(connection_id, "프로젝트 ID와 사용자 입력이 필요합니다")
        
        # 1단계: 프롬프트 구성 시작
        send_message(connection_id, {
            "type": "progress",
            "step": "🔧 프롬프트 카드를 분석하고 있습니다...",
            "progress": 10,
            "sessionId": project_id
        })
        
        # 프롬프트 구성
        final_prompt = build_final_prompt(project_id, user_input, chat_history, prompt_cards)
        
        # 2단계: AI 모델 준비
        send_message(connection_id, {
            "type": "progress", 
            "step": "🤖 AI 모델을 준비하고 있습니다...",
            "progress": 25,
            "sessionId": project_id
        })
        
        # Bedrock 스트리밍 요청
        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": final_prompt}],
            "temperature": 0.3,
            "top_p": 0.9,
        }
        
        # 3단계: 스트리밍 시작
        send_message(connection_id, {
            "type": "progress",
            "step": "✍️ AI가 응답을 실시간으로 생성하고 있습니다...",
            "progress": 40,
            "sessionId": project_id
        })
        
        # Bedrock 스트리밍 응답 처리
        response_stream = bedrock_client.invoke_model_with_response_stream(
            modelId=MODEL_ID,
            body=json.dumps(request_body)
        )
        
        full_response = ""
        
        # 실시간 청크 전송
        for event in response_stream.get("body"):
            chunk = json.loads(event["chunk"]["bytes"].decode())
            
            if chunk['type'] == 'content_block_delta':
                text = chunk['delta']['text']
                full_response += text
                
                # 즉시 클라이언트로 전송
                send_message(connection_id, {
                    "type": "stream_chunk",
                    "content": text,
                    "sessionId": project_id
                })
        
        # 4단계: 스트리밍 완료
        send_message(connection_id, {
            "type": "progress",
            "step": "✅ 응답 생성이 완료되었습니다!",
            "progress": 100,
            "sessionId": project_id
        })
        
        # 최종 완료 알림
        send_message(connection_id, {
            "type": "stream_complete", 
            "fullContent": full_response,
            "sessionId": project_id
        })
        
        # 메시지 저장 (conversation_id와 user_sub가 있는 경우)
        if conversation_id and user_sub:
            save_conversation_messages(conversation_id, user_sub, user_input, full_response)
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': '스트리밍 완료'})
        }
        
    except Exception as e:
        print(f"스트리밍 처리 오류: {traceback.format_exc()}")
        send_error(connection_id, f"스트리밍 오류: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def build_final_prompt(project_id, user_input, chat_history, prompt_cards):
    """
    프론트엔드에서 전송된 프롬프트 카드와 채팅 히스토리를 사용하여 최종 프롬프트 구성
    """
    try:
        print(f"WebSocket 프롬프트 구성 시작: 프로젝트 ID={project_id}")
        print(f"전달받은 프롬프트 카드 수: {len(prompt_cards)}")
        print(f"전달받은 채팅 히스토리 수: {len(chat_history)}")
        
        # 프론트엔드에서 전송된 프롬프트 카드 사용
        system_prompt_parts = []
        for card in prompt_cards:
            prompt_text = card.get('prompt_text', '').strip()
            if prompt_text:
                title = card.get('title', 'Untitled')
                print(f"WebSocket 프롬프트 카드 적용: '{title}' ({len(prompt_text)}자)")
                system_prompt_parts.append(prompt_text)
        
        system_prompt = "\n\n".join(system_prompt_parts)
        print(f"WebSocket 시스템 프롬프트 길이: {len(system_prompt)}자")
        
        # 채팅 히스토리 구성
        history_parts = []
        for msg in chat_history:
            role = msg.get('role', '')
            content = msg.get('content', '')
            if role and content:
                if role == 'user':
                    history_parts.append(f"Human: {content}")
                elif role == 'assistant':
                    history_parts.append(f"Assistant: {content}")
        
        history_str = "\n\n".join(history_parts)
        print(f"WebSocket 채팅 히스토리 길이: {len(history_str)}자")
        
        # 최종 프롬프트 구성
        prompt_parts = []
        
        # 1. 시스템 프롬프트 (역할, 지침 등)
        if system_prompt:
            prompt_parts.append(system_prompt)
        
        # 2. 대화 히스토리
        if history_str:
            prompt_parts.append(history_str)
        
        # 3. 현재 사용자 입력
        prompt_parts.append(f"Human: {user_input}")
        prompt_parts.append("Assistant:")
        
        final_prompt = "\n\n".join(prompt_parts)
        print(f"WebSocket 최종 프롬프트 길이: {len(final_prompt)}자")
        
        return final_prompt
        
    except Exception as e:
        print(f"WebSocket 프롬프트 구성 오류: {traceback.format_exc()}")
        # 오류 발생 시 기본 프롬프트 반환 (히스토리 포함)
        try:
            history_str = "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
            if history_str:
                return f"{history_str}\n\nHuman: {user_input}\n\nAssistant:"
            else:
                return f"Human: {user_input}\n\nAssistant:"
        except:
            return f"Human: {user_input}\n\nAssistant:"

def send_message(connection_id, message):
    """
    WebSocket 클라이언트로 메시지 전송
    """
    try:
        apigateway_client.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps(message)
        )
    except Exception as e:
        print(f"메시지 전송 실패: {connection_id}, 오류: {str(e)}")
        # 연결이 끊어진 경우 DynamoDB에서 제거
        if 'GoneException' in str(e):
            try:
                dynamodb_client.delete_item(
                    TableName=CONNECTIONS_TABLE,
                    Key={'connectionId': {'S': connection_id}}
                )
            except:
                pass

def send_error(connection_id, error_message):
    """
    오류 메시지 전송
    """
    send_message(connection_id, {
        "type": "error",
        "message": error_message,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {
        'statusCode': 400,
        'body': json.dumps({'error': error_message})
    }

def save_conversation_messages(conversation_id, user_sub, user_input, assistant_response):
    """
    대화 메시지를 DynamoDB에 저장
    """
    try:
        now = datetime.now(timezone.utc)
        user_timestamp = now.isoformat()
        assistant_timestamp = (now.replace(microsecond=now.microsecond + 1000)).isoformat()
        
        # Calculate TTL (180 days from now)
        ttl = int(now.timestamp() + (180 * 24 * 60 * 60))
        
        # 사용자 메시지 저장
        user_message = {
            'PK': f'CONV#{conversation_id}',
            'SK': f'TS#{user_timestamp}',
            'role': 'user',
            'content': user_input,
            'tokenCount': estimate_token_count(user_input),
            'ttl': ttl
        }
        
        # 어시스턴트 메시지 저장
        assistant_message = {
            'PK': f'CONV#{conversation_id}',
            'SK': f'TS#{assistant_timestamp}',
            'role': 'assistant', 
            'content': assistant_response,
            'tokenCount': estimate_token_count(assistant_response),
            'ttl': ttl
        }
        
        # 배치로 메시지 저장
        with messages_table.batch_writer() as batch:
            batch.put_item(Item=user_message)
            batch.put_item(Item=assistant_message)
        
        # 대화 활동 시간 및 토큰 카운트 업데이트
        total_tokens = user_message['tokenCount'] + assistant_message['tokenCount']
        update_conversation_activity(conversation_id, user_sub, total_tokens)
        
        print(f"메시지 저장 완료: {conversation_id}, 토큰: {total_tokens}")
        
    except Exception as e:
        print(f"메시지 저장 오류: {str(e)}")
        print(traceback.format_exc())

def update_conversation_activity(conversation_id, user_sub, token_count):
    """
    대화의 마지막 활동 시간과 토큰 합계 업데이트
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        conversations_table.update_item(
            Key={
                'PK': f'USER#{user_sub}',
                'SK': f'CONV#{conversation_id}'
            },
            UpdateExpression='SET lastActivityAt = :activity, tokenSum = tokenSum + :tokens',
            ExpressionAttributeValues={
                ':activity': now,
                ':tokens': token_count
            }
        )
        
    except Exception as e:
        print(f"대화 활동 업데이트 오류: {str(e)}")

def estimate_token_count(text):
    """
    간단한 토큰 수 추정 (대략 4자 = 1토큰)
    실제 환경에서는 tokenizer 라이브러리 사용 권장
    """
    if not text:
        return 0
    return max(1, len(text) // 4)
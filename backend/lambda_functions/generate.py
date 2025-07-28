import json
import boto3
import traceback
import time
from datetime import datetime
from typing import Dict, Any, Optional

# AWS 클라이언트 초기화
bedrock_client = boto3.client('bedrock-runtime', region_name='ap-northeast-2')
dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-2')

# 모델 설정
MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0"

def lambda_handler(event, context):
    """
    AWS Lambda 핸들러: 제목 생성 및 스트리밍 처리
    """
    try:
        print(f"📨 요청 수신: {json.dumps(event, ensure_ascii=False, default=str)}")
        
        # HTTP 메서드 확인
        http_method = event.get('httpMethod', 'POST')
        path = event.get('path', '')
        
        # 경로에서 프로젝트 ID 추출
        path_parts = path.strip('/').split('/')
        project_id = None
        
        for i, part in enumerate(path_parts):
            if part == 'projects' and i + 1 < len(path_parts):
                project_id = path_parts[i + 1]
                break
        
        if not project_id:
            return create_error_response(400, "프로젝트 ID가 필요합니다")
        
        # 🔧 GET 요청 처리 (SSE용)
        if http_method == 'GET':
            query_params = event.get('queryStringParameters') or {}
            
            body = {
                'userInput': query_params.get('userInput', ''),
                'chat_history': json.loads(query_params.get('chat_history', '[]')),
            }
            
            # 입력 검증
            if not body.get('userInput', '').strip():
                return create_sse_error_response("사용자 입력이 필요합니다")
                
        # 🔧 POST 요청 처리 (기존 방식)
        else:
            # POST 요청 본문 파싱
            if isinstance(event.get('body'), str):
                body = json.loads(event['body'])
            else:
                body = event.get('body', {})
            
            # 입력 검증
            if not body.get('userInput', '').strip():
                return create_error_response(400, "사용자 입력이 필요합니다")
        
        # 스트리밍 요청 처리
        if '/stream' in path:
            return handle_streaming_generation(project_id, body, context, http_method)
        else:
            return handle_standard_generation(project_id, body, context)
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {str(e)}")
        return create_error_response(400, "잘못된 JSON 형식입니다")
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {str(e)}")
        print(f"❌ 오류 상세: {traceback.format_exc()}")
        return create_error_response(500, "내부 서버 오류가 발생했습니다")

def handle_streaming_generation(project_id, body, context, http_method='POST'):
    """
    🔧 개선된 스트리밍 생성 처리 - SSE 지원
    """
    try:
        user_input = body.get('userInput', '')
        chat_history = body.get('chat_history', [])
        
        print(f"🔄 스트리밍 생성 시작: {project_id}, 입력 길이: {len(user_input)}, 메서드: {http_method}")
        
        # 프롬프트 구성
        final_prompt = build_final_prompt(project_id, user_input, chat_history)
        
        # 🔧 SSE 응답 헤더 설정
        headers = {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, Cache-Control, Connection',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Expose-Headers': 'Content-Type, Cache-Control, Connection',
        }
        
        # Bedrock 스트리밍 호출
        start_time = time.time()
        response = bedrock_client.invoke_model_with_response_stream(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": final_prompt}],
                "temperature": 0.7,
                "top_p": 0.9,
            }),
            contentType="application/json",
            accept="application/json"
        )
        
        # 🔧 SSE 형태로 스트리밍 응답 생성
        streaming_chunks = []
        full_response = ""
        chunk_count = 0
        
        for event in response['body']:
            if 'chunk' in event:
                chunk_data = json.loads(event['chunk']['bytes'].decode('utf-8'))
                
                if chunk_data.get('type') == 'content_block_delta':
                    if 'delta' in chunk_data and 'text' in chunk_data['delta']:
                        chunk_text = chunk_data['delta']['text']
                        full_response += chunk_text
                        chunk_count += 1
                        
                        # 🔧 SSE 형태로 청크 데이터 포맷팅
                        sse_data = {
                            'response': chunk_text,
                            'sessionId': project_id,
                            'timestamp': datetime.now().isoformat(),
                            'type': 'chunk',
                            'chunkNumber': chunk_count
                        }
                        
                        streaming_chunks.append(f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n")
        
        # 🔧 완료 이벤트 추가
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        completion_data = {
            'response': '',
            'sessionId': project_id,
            'timestamp': datetime.now().isoformat(),
            'type': 'complete',
            'fullResponse': full_response,
            'processingTime': processing_time,
            'totalChunks': chunk_count,
            'responseLength': len(full_response)
        }
        streaming_chunks.append(f"data: {json.dumps(completion_data, ensure_ascii=False)}\n\n")
        
        print(f"✅ 스트리밍 완료: {processing_time}초, {chunk_count}개 청크, {len(full_response)}자")
        
        # 🔧 SSE 응답 반환
        return {
            'statusCode': 200,
            'headers': headers,
            'body': ''.join(streaming_chunks),
            'isBase64Encoded': False
        }
        
    except Exception as e:
        print(f"❌ 스트리밍 생성 오류: {str(e)}")
        print(f"❌ 오류 상세: {traceback.format_exc()}")
        
        headers = {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Access-Control-Allow-Origin': '*',
        }
        
        error_data = {
            'error': str(e),
            'sessionId': project_id,
            'timestamp': datetime.now().isoformat(),
            'type': 'error'
        }
        
        return {
            'statusCode': 500,
            'headers': headers,
            'body': f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        }

def handle_standard_generation(project_id, body, context):
    """
    일반 제목 생성 처리 (비스트리밍)
    """
    try:
        user_input = body.get('userInput', '')
        chat_history = body.get('chat_history', [])
        
        print(f"📝 일반 생성 시작: {project_id}, 입력 길이: {len(user_input)}")
        
        # 프롬프트 구성
        final_prompt = build_final_prompt(project_id, user_input, chat_history)
        
        # Bedrock 호출
        start_time = time.time()
        response = bedrock_client.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": final_prompt}],
                "temperature": 0.7,
                "top_p": 0.9,
            }),
            contentType="application/json",
            accept="application/json"
        )
        
        # 응답 파싱
        response_body = json.loads(response['body'].read())
        generated_text = response_body['content'][0]['text']
        
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        print(f"✅ 일반 생성 완료: {processing_time}초, {len(generated_text)}자")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            },
            'body': json.dumps({
                'result': generated_text,
                'mode': 'standard',
                'processing_time': processing_time,
                'timestamp': datetime.now().isoformat(),
                'message': '제목 생성이 완료되었습니다.'
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"❌ 일반 생성 오류: {str(e)}")
        print(f"❌ 오류 상세: {traceback.format_exc()}")
        return create_error_response(500, f"제목 생성 중 오류가 발생했습니다: {str(e)}")

def build_final_prompt(project_id: str, user_input: str, chat_history: list) -> str:
    """
    프롬프트 카드를 기반으로 최종 프롬프트 구성
    """
    try:
        # 프롬프트 카드 로드
        prompt_cards = load_prompt_cards(project_id)
        
        if not prompt_cards:
            return f"사용자 요청: {user_input}"
        
        # 프롬프트 카드를 stepOrder 순으로 정렬
        sorted_cards = sorted(prompt_cards, key=lambda x: x.get('stepOrder', 999))
        
        # 시스템 프롬프트 구성
        system_parts = []
        for card in sorted_cards:
            if card.get('isActive', True) and card.get('content'):
                system_parts.append(f"[{card.get('title', '단계')}]\n{card['content']}")
        
        system_prompt = "\n\n".join(system_parts) if system_parts else "도움이 되는 AI 어시스턴트입니다."
        
        # 채팅 히스토리 포함
        context_parts = [system_prompt]
        
        if chat_history:
            context_parts.append("\n[이전 대화 내용]")
            for msg in chat_history[-5:]:  # 최근 5개만 포함
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                if content.strip():
                    context_parts.append(f"{role}: {content}")
        
        context_parts.append(f"\n[현재 요청]\n사용자: {user_input}")
        context_parts.append("\n어시스턴트:")
        
        return "\n".join(context_parts)
        
    except Exception as e:
        print(f"⚠️ 프롬프트 구성 오류: {str(e)}")
        return f"사용자 요청: {user_input}"

def load_prompt_cards(project_id: str) -> list:
    """
    프로젝트의 프롬프트 카드 로드
    """
    try:
        table = dynamodb.Table('ChatbotPrompts')
        
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('projectId').eq(project_id),
            ProjectionExpression='promptId, title, content, stepOrder, isActive'
        )
        
        return response.get('Items', [])
        
    except Exception as e:
        print(f"⚠️ 프롬프트 카드 로드 실패: {str(e)}")
        return []

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """표준 오류 응답 생성"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        },
        'body': json.dumps({
            'error': message,
            'timestamp': datetime.now().isoformat()
        }, ensure_ascii=False)
    }

def create_sse_error_response(error_message: str) -> Dict[str, Any]:
    """SSE 형태의 오류 응답 생성"""
    headers = {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    }
    
    error_data = {
        'error': error_message,
        'timestamp': datetime.now().isoformat(),
        'type': 'error'
    }
    
    return {
        'statusCode': 400,
        'headers': headers,
        'body': f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    } 
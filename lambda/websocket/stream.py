"""
WebSocket 실시간 스트리밍 Lambda 함수
"""
import json
import os
import re
import sys
import boto3
import traceback
import logging
from datetime import datetime, timezone

# Enhanced Agent System import 추가
sys.path.append('/opt/python')  # Lambda Layer 경로
sys.path.append('.')

# Logger 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Smart Query Router 로드 시도 (최우선)
try:
    from smart_router.query_router import SmartQueryRouter
    logger.info("🎯 SmartQueryRouter 로드 성공 (WebSocket)")
    SMART_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"SmartQueryRouter 로드 실패 (WebSocket): {str(e)}")
    SMART_ROUTER_AVAILABLE = False

# Fallback: Enhanced Agent System 로드
try:
    from workflow_engine.conditional_execution import ConditionalExecutionEngine
    logger.info("✅ Enhanced Agent System 로드 성공 (WebSocket)")
    ENHANCED_AGENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Enhanced Agent System 로드 실패 (WebSocket): {str(e)}")
    ENHANCED_AGENTS_AVAILABLE = False

# AWS 클라이언트
bedrock_client = boto3.client("bedrock-runtime")
bedrock_agent_client = boto3.client("bedrock-agent-runtime")
dynamodb_client = boto3.client("dynamodb")
dynamodb_resource = boto3.resource("dynamodb")
apigateway_client = boto3.client("apigatewaymanagementapi")

# 환경 변수
CONNECTIONS_TABLE = os.environ.get('CONNECTIONS_TABLE')
PROMPT_META_TABLE = os.environ.get('PROMPT_META_TABLE')
PROMPT_BUCKET = os.environ.get('PROMPT_BUCKET')
CONVERSATIONS_TABLE = os.environ.get('CONVERSATIONS_TABLE', 'Conversations')
MESSAGES_TABLE = os.environ.get('MESSAGES_TABLE', 'Messages')
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', 'PGQV3JXPET')
MODEL_ID = "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"

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
        model_id = data.get('modelId', MODEL_ID)  # Get model ID from request or use default
        
        print(f"🔍 [DEBUG] WebSocket 스트림 요청 받음:")
        print(f"  - project_id: {project_id}")
        print(f"  - user_input: {user_input[:50]}..." if user_input else "  - user_input: None")
        print(f"  - conversation_id: {conversation_id}")
        print(f"  - conversation_id type: {type(conversation_id)}")
        print(f"  - conversation_id is None: {conversation_id is None}")
        print(f"  - user_sub: {user_sub}")
        print(f"  - chat_history length: {len(chat_history)}")
        
        if not project_id or not user_input:
            return send_error(connection_id, "프로젝트 ID와 사용자 입력이 필요합니다")
        
        # Smart Query Router 사용 (최우선)
        if SMART_ROUTER_AVAILABLE:
            logger.info("🎯 SmartQueryRouter로 질문 처리 (WebSocket)")
            send_message(connection_id, {
                "type": "progress", 
                "step": "🎯 Smart Query Router가 조건별 분기를 결정하고 있습니다...",
                "progress": 10,
                "sessionId": project_id
            })
            
            # Smart Query Router 실행
            smart_result = execute_smart_router_workflow(user_input, project_id, chat_history, model_id, connection_id)
            
            if smart_result and smart_result.get('success'):
                final_response = smart_result.get('final_answer', '')
                knowledge_sources = smart_result.get('sources', [])
                thinking_process = smart_result.get('thinking_process', [])
            else:
                logger.warning("SmartQueryRouter 실행 실패, Enhanced Agent System으로 fallback")
                # Fallback to Enhanced Agent System
                if ENHANCED_AGENTS_AVAILABLE:
                    enhanced_result = execute_enhanced_workflow(user_input, project_id, chat_history, model_id, connection_id)
                    if enhanced_result and enhanced_result.get('success'):
                        final_response = enhanced_result.get('final_answer', '')
                        knowledge_sources = enhanced_result.get('sources', [])
                        thinking_process = enhanced_result.get('thinking_process', [])
                    else:
                        final_response = "죄송합니다. 현재 서비스에 일시적인 문제가 있습니다."
                        knowledge_sources = []
                        thinking_process = []
                else:
                    final_response = "죄송합니다. 현재 서비스에 일시적인 문제가 있습니다."
                    knowledge_sources = []
                    thinking_process = []

        # Fallback 1: Enhanced Agent System 
        elif ENHANCED_AGENTS_AVAILABLE:
            logger.info("🚀 Enhanced Agent System으로 질문 처리 (Fallback)")
            send_message(connection_id, {
                "type": "progress", 
                "step": "🧠 Enhanced Agent System이 질문을 분석하고 있습니다...",
                "progress": 10,
                "sessionId": project_id
            })
            
            # Enhanced Agent System 실행
            enhanced_result = execute_enhanced_workflow(user_input, project_id, chat_history, model_id, connection_id)
            
            if enhanced_result and enhanced_result.get('success'):
                final_response = enhanced_result.get('final_answer', '')
                knowledge_sources = enhanced_result.get('sources', [])
                thinking_process = enhanced_result.get('thinking_process', [])
            else:
                # Enhanced Agent System 실패 시 fallback
                logger.warning("Enhanced Agent System 실행 실패, 기존 시스템 사용")
                final_response = "죄송합니다. 현재 서비스에 일시적인 문제가 있습니다."
                knowledge_sources = []
                thinking_process = []
        # Fallback 2: 기존 시스템 사용 
        else:
            logger.info("🔄 기존 Knowledge Base 검색 시스템 사용 (최종 Fallback)")
            send_message(connection_id, {
                "type": "progress",
                "step": "📚 서울경제신문 뉴스 데이터를 검색하고 있습니다...",
                "progress": 10,
                "sessionId": project_id
            })
            
            # Knowledge Base 검색
            knowledge_result = search_knowledge_base(user_input)
            knowledge_context = knowledge_result.get('context', '') if isinstance(knowledge_result, dict) else knowledge_result
            knowledge_sources = knowledge_result.get('sources', []) if isinstance(knowledge_result, dict) else []
            thinking_process = []  # 기존 시스템에서는 사고 과정 없음
            
            # 프롬프트 구성 (Knowledge Base 컨텍스트 포함)
            final_prompt = build_final_prompt(project_id, user_input, chat_history, prompt_cards, knowledge_context)
            
            # 기존 시스템 사용 - Bedrock 스트리밍 요청
            send_message(connection_id, {
                "type": "progress", 
                "step": "🤖 AI 모델을 준비하고 있습니다...",
                "progress": 25,
                "sessionId": project_id
            })
            
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": final_prompt}],
                "temperature": 0.3,
                "top_p": 0.9,
            }
            
            send_message(connection_id, {
                "type": "progress",
                "step": "✍️ AI가 응답을 실시간으로 생성하고 있습니다...",
                "progress": 40,
                "sessionId": project_id
            })
            
            # Bedrock 스트리밍 응답 처리
            print(f"🤖 Using model: {model_id}")
            response_stream = bedrock_client.invoke_model_with_response_stream(
                modelId=model_id,
                body=json.dumps(request_body)
            )
            
            final_response = ""
            
            # 실시간 청크 전송
            for event in response_stream.get("body"):
                chunk = json.loads(event["chunk"]["bytes"].decode())
                
                if chunk['type'] == 'content_block_delta':
                    text = chunk['delta']['text']
                    final_response += text
                    
                    # 즉시 클라이언트로 전송
                    send_message(connection_id, {
                        "type": "stream_chunk",
                        "content": text,
                        "sessionId": project_id
                    })
        
        # Enhanced Agent System 또는 기존 시스템 응답 처리
        if 'final_response' in locals():
            # 기존 시스템에서 스트리밍된 응답
            full_response = final_response
        else:
            # final_response가 없는 경우 빈 문자열로 초기화
            full_response = ""
        
        # 4단계: 스트리밍 완료
        send_message(connection_id, {
            "type": "progress",
            "step": "✅ 응답 생성이 완료되었습니다!",
            "progress": 100,
            "sessionId": project_id
        })
        
        # SmartQueryRouter 또는 Enhanced Agent System을 사용한 경우 최종 답변을 스트리밍 형태로 전송
        if ((SMART_ROUTER_AVAILABLE and 'smart_result' in locals() and smart_result and smart_result.get('success')) or
            (ENHANCED_AGENTS_AVAILABLE and 'enhanced_result' in locals() and enhanced_result and enhanced_result.get('success'))):
            
            # 🎯 실시간 타이핑 애니메이션을 위한 청크 스트리밍
            import time
            
            # 더 작은 청크 크기로 자연스러운 타이핑 효과
            chunk_size = 3  # 3글자씩 (한글 기준으로 자연스러움)
            typing_delay = 0.03  # 30ms 딜레이 (적당한 타이핑 속도)
            
            logger.info(f"🎬 타이핑 애니메이션 시작: 총 {len(final_response)}글자, {chunk_size}글자씩 청크")
            
            for i in range(0, len(final_response), chunk_size):
                chunk = final_response[i:i+chunk_size]
                
                # 청크 전송
                send_message(connection_id, {
                    "type": "stream_chunk",
                    "content": chunk,
                    "sessionId": project_id,
                    "chunk_index": i // chunk_size,
                    "total_chunks": (len(final_response) + chunk_size - 1) // chunk_size
                })
                
                logger.info(f"📤 청크 전송: '{chunk}' (index: {i // chunk_size})")
                
                # 자연스러운 타이핑 속도를 위한 딜레이
                time.sleep(typing_delay)
            
            # 🎬 타이핑 완료 신호
            send_message(connection_id, {
                "type": "stream_complete",
                "fullContent": final_response,
                "sources": smart_result.get('sources', []) if 'smart_result' in locals() else enhanced_result.get('sources', []) if 'enhanced_result' in locals() else [],
                "thinkingProcess": smart_result.get('thinking_process', []) if 'smart_result' in locals() else enhanced_result.get('thinking_process', []) if 'enhanced_result' in locals() else [],
                "sessionId": project_id
            })
            
            logger.info("✅ 실시간 타이핑 애니메이션 완료!")
        
        # 최종 완료 알림 (소스 정보 및 사고 과정 포함)
        print(f"🔍 [DEBUG] stream_complete 메시지 전송:")
        print(f"  - sources 개수: {len(knowledge_sources)}")
        print(f"  - thinking_process 개수: {len(thinking_process) if 'thinking_process' in locals() else 0}")
        
        send_message(connection_id, {
            "type": "stream_complete", 
            "fullContent": final_response,
            "sources": knowledge_sources,
            "thinkingProcess": thinking_process if 'thinking_process' in locals() else [],
            "sessionId": project_id
        })
        
        # 메시지 저장 (conversation_id와 user_sub가 있는 경우)
        if conversation_id and user_sub:
            print(f"🔍 [DEBUG] 메시지 저장 시작:")
            print(f"  - conversation_id: {conversation_id}")
            print(f"  - user_sub: {user_sub}")
            print(f"  - user_input length: {len(user_input)}")
            print(f"  - assistant_response length: {len(full_response)}")
            save_conversation_messages(conversation_id, user_sub, user_input, full_response)
        else:
            print(f"🔍 [DEBUG] 메시지 저장 건너뜀:")
            print(f"  - conversation_id: {conversation_id} (is None: {conversation_id is None})")
            print(f"  - user_sub: {user_sub} (is None: {user_sub is None})")
            print(f"  - 메시지가 저장되지 않습니다!")
        
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

def execute_smart_router_workflow(user_input, project_id, chat_history, model_id, connection_id):
    """
    Smart Query Router 워크플로우 실행 (WebSocket용)
    """
    try:
        if not SMART_ROUTER_AVAILABLE:
            return None
            
        logger.info(f"🎯 SmartQueryRouter 워크플로우 실행 (WebSocket): {user_input}")
        
        # 1. SmartQueryRouter 초기화
        smart_router = SmartQueryRouter()
        
        # 2. 사용자 컨텍스트 구성
        user_context = {
            "project_id": project_id,
            "chat_history": chat_history,
            "model_id": model_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # 진행 상황 업데이트
        send_message(connection_id, {
            "type": "progress",
            "step": "🧠 질문을 분석하고 최적의 라우팅을 결정하고 있습니다...",
            "progress": 30,
            "sessionId": project_id
        })
        
        # 3. 메인 라우팅 및 실행
        router_result = smart_router.route_and_execute(
            query=user_input,
            context=user_context
        )
        
        send_message(connection_id, {
            "type": "progress",
            "step": "✨ Smart Query Router가 조건별 분기로 답변을 생성했습니다!",
            "progress": 90,
            "sessionId": project_id
        })
        
        # 4. 결과 처리
        if router_result["success"]:
            final_result = router_result["result"]
            return {
                "success": True,
                "final_answer": final_result.get("answer", "답변을 생성할 수 없습니다."),
                "sources": final_result.get("sources", []),
                "thinking_process": router_result.get("thinking_process", []),
                "routing_info": router_result.get("routing_info", {}),
                "execution_time": router_result.get("execution_time", 0)
            }
        else:
            logger.error(f"SmartQueryRouter 실행 실패: {router_result.get('error')}")
            return {
                "success": False,
                "error": router_result.get("error", "알 수 없는 오류")
            }
            
    except Exception as e:
        logger.error(f"SmartQueryRouter 워크플로우 오류 (WebSocket): {str(e)}")
        logger.error(f"상세 오류: {traceback.format_exc()}")
        return {
            "success": False,
            "error": str(e)
        }


def execute_enhanced_workflow(user_input, project_id, chat_history, model_id, connection_id):
    """
    Enhanced Agent System 워크플로우 실행 (WebSocket용)
    """
    try:
        if not ENHANCED_AGENTS_AVAILABLE:
            return None
            
        logger.info(f"🚀 Enhanced Agent System 워크플로우 실행: {user_input}")
        
        # 1. ConditionalExecutionEngine 초기화
        execution_engine = ConditionalExecutionEngine()
        
        # 2. 사용자 컨텍스트 구성
        user_context = {
            "project_id": project_id,
            "chat_history": chat_history,
            "model_id": model_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # 3. 실행 옵션 설정
        execution_options = {
            "enable_external_search": True,  # Perplexity 검색 활성화
            "enable_date_intelligence": True,
            "enable_few_shot": True,
            "debug": True
        }
        
        # 진행 상황 업데이트
        send_message(connection_id, {
            "type": "progress",
            "step": "🔍 질문을 분석하고 최적의 검색 전략을 수립하고 있습니다...",
            "progress": 30,
            "sessionId": project_id
        })
        
        # 4. 메인 워크플로우 실행
        workflow_result = execution_engine.execute_workflow(
            query=user_input,
            user_context=user_context,
            execution_options=execution_options
        )
        
        send_message(connection_id, {
            "type": "progress",
            "step": "✨ Enhanced Agent System이 답변을 생성하고 있습니다...",
            "progress": 80,
            "sessionId": project_id
        })
        
        if workflow_result and workflow_result.get('success'):
            logger.info("✅ Enhanced Agent System 워크플로우 성공")
            
            # workflow_result에서 올바른 필드명으로 결과 추출
            result_data = workflow_result.get('result', {})
            final_answer = result_data.get('answer', '')
            sources = result_data.get('sources', [])
            
            return {
                'success': True,
                'final_answer': final_answer,
                'sources': sources,
                'thinking_process': workflow_result.get('thinking_process', []),
                'search_type': 'enhanced_agents',
                'timestamp': datetime.now().isoformat()
            }
        else:
            logger.error(f"❌ Enhanced Agent System 워크플로우 실패: {workflow_result}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Enhanced Agent System 실행 오류: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def build_final_prompt(project_id, user_input, chat_history, prompt_cards, knowledge_context=""):
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
        
        # 2. Knowledge Base 컨텍스트 (있는 경우)
        if knowledge_context:
            prompt_parts.append(knowledge_context)
            
            # Knowledge Base 사용 시 각주 가이드라인 추가
            citation_guideline = """
=== 중요한 답변 가이드라인 ===
위의 서울경제신문 뉴스를 참고하여 답변할 때는 반드시 다음 규칙을 따르세요:

1. 뉴스 내용을 인용할 때는 [1], [2], [3] 형태의 각주 번호를 사용하세요
2. 각 뉴스 기사의 정보를 사용할 때마다 해당 번호를 문장 끝에 표시하세요
3. 예시: "서울경제신문에 따르면 GDP가 상승했습니다[1]"
4. 여러 기사를 참고할 때는 [1][2] 형태로 연결하여 사용하세요
5. 답변은 한국어로 작성하고, 전문적이면서도 이해하기 쉽게 설명하세요

각주는 클릭 가능한 링크로 변환되어 사용자가 원문을 확인할 수 있습니다.
"""
            prompt_parts.append(citation_guideline)
        
        # 3. 대화 히스토리
        if history_str:
            prompt_parts.append(history_str)
        
        # 4. 현재 사용자 입력
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
        print(f"🔍 [DEBUG] save_conversation_messages 시작:")
        print(f"  - conversation_id: {conversation_id}")
        print(f"  - user_sub: {user_sub}")
        
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
        
        print(f"🔍 [DEBUG] DynamoDB에 저장할 메시지들:")
        print(f"  - User message PK: {user_message['PK']}")
        print(f"  - User message SK: {user_message['SK']}")
        print(f"  - Assistant message PK: {assistant_message['PK']}")
        print(f"  - Assistant message SK: {assistant_message['SK']}")
        
        # 배치로 메시지 저장
        with messages_table.batch_writer() as batch:
            batch.put_item(Item=user_message)
            batch.put_item(Item=assistant_message)
        
        # 대화 활동 시간 및 토큰 카운트 업데이트
        total_tokens = user_message['tokenCount'] + assistant_message['tokenCount']
        update_conversation_activity(conversation_id, user_sub, total_tokens)
        
        print(f"🔍 [DEBUG] 메시지 저장 완료: {conversation_id}, 토큰: {total_tokens}")
        
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

def search_knowledge_base(query):
    """
    Knowledge Base를 사용한 뉴스 검색
    """
    try:
        print(f"📚 Knowledge Base 검색 시작: {query}")
        
        response = bedrock_agent_client.retrieve(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 5,
                    'overrideSearchType': 'HYBRID'
                }
            }
        )
        
        # 검색 결과를 텍스트와 메타데이터로 변환
        contexts = []
        sources = []
        seen = set()  # 중복 방지용
        skipped_count = 0
        
        for idx, result in enumerate(response.get('retrievalResults', [])[:5], 1):
            text = result.get('content', {}).get('text', '')
            metadata = result.get('metadata', {})
            
            if not text.strip():
                continue
                
            # Knowledge Base에서 반환된 데이터 파싱 (실제 형식에 맞게 수정)
            articles = []
            
            # 각 검색 결과는 이미 개별 기사임
            lines = text.splitlines()
            if lines:
                # 첫 번째 줄이 제목인 경우가 많음
                title_line = lines[0].strip()
                if title_line.startswith('"') and title_line.endswith('"'):
                    title_line = title_line[1:-1]  # 따옴표 제거
                
                current = {"title": title_line}
                
                # 메타데이터 추출
                for line in lines[1:]:
                    line = line.strip()
                    if line.startswith("**") and ":**" in line:
                        try:
                            # **발행일:** 2007-09-30T00:00:00.000+09:00 형식 파싱
                            key_end = line.find(":**")
                            if key_end > 2:
                                key = line[2:key_end].strip()
                                value = line[key_end + 3:].strip()
                                current[key] = value
                        except Exception as e:
                            print(f"메타데이터 파싱 오류: {e}")
                    elif line.startswith("**내용:**"):
                        break  # 내용 부분은 건너뜀
                
                if current.get("title"):
                    articles.append(current)
            
            print(f"🔍 파싱된 기사 수: {len(articles)}")
            
            # 기사별 처리
            for article_idx, a in enumerate(articles, 1):
                url = a.get("URL", "")
                news_id = a.get("뉴스 ID", "")
                title = a.get("title", "")
                published_date = a.get("발행일", "")
                
                print(f"🔍 기사 {article_idx}: title='{title[:50]}...' url='{url[:30]}...' news_id='{news_id[:20]}...' date='{published_date[:20]}...'")
                
                # E단계: URL 없으면 fallback으로 첫 번째 http 링크 시도
                if not url:
                    fallback_url_match = re.search(r'https?://\S+', text)
                    if fallback_url_match:
                        url = fallback_url_match.group(0)
                        a["URL"] = url
                        print(f"🔄 fallback URL 발견: {url[:50]}...")
                
                # 필수 필드 검사 - title 필수, URL은 선택사항으로 변경
                if not title:
                    print(f"📄 기사 {article_idx} SKIP: 제목 누락")
                    skipped_count += 1
                    continue
                
                # URL이 있는 경우 중복 검사
                if url and url in seen:
                    print(f"📄 기사 {article_idx} SKIP: 중복 URL ({url[:30]}...)")
                    skipped_count += 1
                    continue
                if url:
                    seen.add(url)
                
                # 뉴스 ID → 날짜 변환 또는 발행일 직접 사용
                formatted_date = ""
                if published_date:
                    # ISO 날짜 형식을 한국어 형식으로 변환
                    try:
                        if "T" in published_date:
                            date_part = published_date.split("T")[0]  # 2007-09-30
                            formatted_date = date_part
                        else:
                            formatted_date = published_date
                    except:
                        formatted_date = published_date
                elif "." in news_id:
                    ts = news_id.split(".")[1][:12]  # yyyymmddHHMM
                    if len(ts) == 12:
                        formatted_date = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[8:10]}:{ts[10:12]}"
                
                # sources 배열에 추가
                source_info = {
                    'id': len(sources) + 1,
                    'title': title,
                    'date': formatted_date,
                    'url': url if url else f"#article-{len(sources) + 1}"  # URL이 없으면 임시 링크
                }
                sources.append(source_info)
                
                # 로그 출력
                print(f"📄 기사 {len(sources)} | {title[:50]}{'...' if len(title) > 50 else ''} | {formatted_date} | {url[:30] if url else '(no URL)'}...")
                
                # 컨텍스트 추가 (제목과 메타데이터만)
                context_text = f"제목: {title}"
                if formatted_date:
                    context_text += f"\n발행일: {formatted_date}"
                if url:
                    context_text += f"\nURL: {url}"
                contexts.append(f"[{len(sources)}] {context_text}")
        
        if contexts:
            knowledge_context = "\\n\\n=== 서울경제신문 관련 뉴스 ===\\n" + "\\n\\n".join(contexts[:3])
            print(f"📚 Knowledge Base 검색 완료: {len(sources)}개 수집, {skipped_count}개 스킵")
            
            # 소스 정보를 반환하기 위해 글로벌 변수나 다른 방법 필요
            # 일단 컨텍스트에 메타데이터 포함
            return {
                'context': knowledge_context,
                'sources': sources
            }
        else:
            print(f"📚 Knowledge Base 검색 결과 없음 ({skipped_count}개 스킵)")
            return {
                'context': "",
                'sources': []
            }
            
    except Exception as e:
        print(f"❌ Knowledge Base 검색 오류: {str(e)}")
        return {
            'context': "",
            'sources': []
        }
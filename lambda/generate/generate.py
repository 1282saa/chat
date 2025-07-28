"""
AI 대화 생성 Lambda 함수 (Enhanced Agent System)
- 새로운 다중 에이전트 시스템 통합
- ReAct + CoT Planning 적용
- 날짜 지능형 처리 및 Perplexity 검색
- Few-shot 기반 답변 생성
- 임계값 기반 조건부 실행
"""
import json
import os
import traceback
import boto3
import logging
import re
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime
import sys

# Logger 설정 (먼저 설정)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 새로운 에이전트 시스템 import
sys.path.append('/opt/python')  # Lambda Layer 경로
sys.path.append('.')

# Smart Query Router import (최우선)
try:
    from smart_router.query_router import SmartQueryRouter
    logger.info("🎯 SmartQueryRouter 로드 성공")
    SMART_ROUTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"SmartQueryRouter 로드 실패: {str(e)}")
    SMART_ROUTER_AVAILABLE = False
except Exception as e:
    logger.error(f"SmartQueryRouter 오류: {str(e)}")
    SMART_ROUTER_AVAILABLE = False

# Fallback: Enhanced Agent System
try:
    from workflow_engine.conditional_execution import ConditionalExecutionEngine
    logger.info("ConditionalExecutionEngine 로드 성공")
    ENHANCED_AGENTS_AVAILABLE = True
    logger.info("Enhanced Agent System Fallback 준비 완료")
    
except ImportError as e:
    logger.warning(f"Enhanced Agent System도 로드 실패: {str(e)}")
    logger.warning(f"상세 오류: {traceback.format_exc()}")
    ENHANCED_AGENTS_AVAILABLE = False
except Exception as e:
    logger.error(f"Enhanced Agent System 오류: {str(e)}")
    logger.error(f"상세 오류: {traceback.format_exc()}")
    ENHANCED_AGENTS_AVAILABLE = False

# --- AWS 클라이언트 및 기본 설정 ---
bedrock_client = boto3.client("bedrock-runtime", region_name=os.environ.get("REGION", "ap-northeast-2"))
bedrock_agent_client = boto3.client("bedrock-agent-runtime", region_name=os.environ.get("REGION", "ap-northeast-2"))
dynamodb_client = boto3.client("dynamodb", region_name=os.environ.get("REGION", "ap-northeast-2"))
PROMPT_META_TABLE = os.environ.get("PROMPT_META_TABLE", "ChatbotPrompts")
# Knowledge Base 설정
KNOWLEDGE_BASE_ID = os.environ.get("KNOWLEDGE_BASE_ID", "PGQV3JXPET")
# Perplexity API 설정
PERPLEXITY_API_KEY = os.environ.get("PERPLEXITY_API_KEY")
# 기본 모델 ID (프론트엔드에서 지정하지 않을 때 사용)
DEFAULT_MODEL_ID = "apac.anthropic.claude-3-haiku-20240307-v1:0"

# 로깅 설정 (위에서 이미 설정됨)

# 지원되는 모델 목록 (Inference Profile IDs)
SUPPORTED_MODELS = {
    # Anthropic Claude 모델들 (Inference Profiles)
    "apac.anthropic.claude-sonnet-4-20250514-v1:0": {"name": "Claude Sonnet 4", "provider": "Anthropic"},
    "apac.anthropic.claude-3-7-sonnet-20250219-v1:0": {"name": "Claude 3.7 Sonnet", "provider": "Anthropic"},
    "apac.anthropic.claude-3-5-sonnet-20241022-v2:0": {"name": "Claude 3.5 Sonnet v2", "provider": "Anthropic"},
    "apac.anthropic.claude-3-5-sonnet-20240620-v1:0": {"name": "Claude 3.5 Sonnet", "provider": "Anthropic"},
    "apac.anthropic.claude-3-haiku-20240307-v1:0": {"name": "Claude 3 Haiku", "provider": "Anthropic"},
    "apac.anthropic.claude-3-sonnet-20240229-v1:0": {"name": "Claude 3 Sonnet", "provider": "Anthropic"},
    
    # Legacy Direct Model IDs (fallback)
    "anthropic.claude-3-haiku-20240307-v1:0": {"name": "Claude 3 Haiku", "provider": "Anthropic"},
    "anthropic.claude-3-sonnet-20240229-v1:0": {"name": "Claude 3 Sonnet", "provider": "Anthropic"},
    
    # Meta Llama 모델들
    "meta.llama4-scout-17b-instruct-v4:0": {"name": "Llama 4 Scout 17B", "provider": "Meta"},
    "meta.llama4-maverick-17b-instruct-v4:0": {"name": "Llama 4 Maverick 17B", "provider": "Meta"},
    "meta.llama3-3-70b-instruct-v1:0": {"name": "Llama 3.3 70B", "provider": "Meta"},
    "meta.llama3-2-11b-instruct-v1:0": {"name": "Llama 3.2 11B Vision", "provider": "Meta"},
    "meta.llama3-2-1b-instruct-v1:0": {"name": "Llama 3.2 1B", "provider": "Meta"},
    "meta.llama3-2-3b-instruct-v1:0": {"name": "Llama 3.2 3B", "provider": "Meta"},
    
    # Amazon Nova 모델들
    "amazon.nova-premier-v1:0": {"name": "Nova Premier", "provider": "Amazon"},
    "amazon.nova-lite-v1:0": {"name": "Nova Lite", "provider": "Amazon"},
    "amazon.nova-micro-v1:0": {"name": "Nova Micro", "provider": "Amazon"},
    "amazon.nova-pro-v1:0": {"name": "Nova Pro", "provider": "Amazon"},
}

def handler(event, context):
    """
    API Gateway 요청을 처리하여 Bedrock 스트리밍 응답을 반환합니다.
    - GET 요청은 EventSource (SSE)를 위해 사용됩니다 (긴 URL 문제로 현재는 비권장).
    - POST 요청이 기본 스트리밍 방식입니다.
    """
    try:
        logger.info("🚀 Handler 시작")
        logger.info(f"🔍 이벤트 수신: {json.dumps(event)}")
        logger.info(f"🔍 SmartRouter 사용 가능: {SMART_ROUTER_AVAILABLE}")
        logger.info(f"🔍 Enhanced Agents 사용 가능: {ENHANCED_AGENTS_AVAILABLE}")
        
        http_method = event.get("httpMethod", "POST")
        path = event.get("path", "")
        project_id = event.get("pathParameters", {}).get("projectId")
        
        logger.info(f"🔍 HTTP Method: {http_method}, Path: {path}, Project ID: {project_id}")

        # 🎯 SmartQueryRouter는 프로젝트 ID 없이도 작동 가능
        if not project_id:
            logger.info("⚡ 프로젝트 ID 없음 - SmartQueryRouter 모드로 실행")
            project_id = "default"  # 기본값 설정

        if not project_id:
            logger.error("❌ 프로젝트 ID 누락")
            return _create_error_response(400, "프로젝트 ID가 필요합니다.")

        # 요청 본문(body) 파싱
        try:
            if http_method == 'GET':
                params = event.get('queryStringParameters') or {}
                user_input = params.get('userInput', '')
                chat_history_str = params.get('chat_history', '[]')
                chat_history = json.loads(chat_history_str)
                model_id = params.get('modelId', DEFAULT_MODEL_ID)
                use_knowledge_base = False
            else: # POST
                body = json.loads(event.get('body', '{}'))
                user_input = body.get('userInput', '')
                chat_history = body.get('chat_history', [])
                prompt_cards = body.get('prompt_cards', [])
                model_id = body.get('modelId', DEFAULT_MODEL_ID)
                use_knowledge_base = body.get('useKnowledgeBase', False)
                
            logger.info(f"🔍 파싱 완료 - user_input: {user_input[:50]}..., use_knowledge_base: {use_knowledge_base}")
                
        except Exception as parse_error:
            logger.error(f"❌ 요청 파싱 오류: {str(parse_error)}")
            return _create_error_response(400, f"요청 파싱 오류: {str(parse_error)}")
            
        if not user_input.strip():
            logger.error("❌ 사용자 입력 누락")
            return _create_error_response(400, "사용자 입력이 필요합니다.")
        
        # 모델 ID 검증
        if model_id not in SUPPORTED_MODELS:
            logger.warning(f"⚠️ 지원되지 않는 모델 ID: {model_id}")
            model_id = DEFAULT_MODEL_ID
        
        logger.info(f"🔍 최종 설정 - 모델: {model_id}, Knowledge Base: {use_knowledge_base}")
        
        # GET 요청일 때 prompt_cards 처리
        if http_method == 'GET':
            prompt_cards = []
        
        logger.info(f"✅ 선택된 모델: {model_id} ({SUPPORTED_MODELS.get(model_id, {}).get('name', 'Unknown')})")
        
        # Knowledge Base 사용 여부에 따른 분기
        if use_knowledge_base:
            logger.info("🎯 Knowledge Base 처리 시작")
            return _handle_knowledge_base_generation(project_id, user_input, chat_history, model_id)
        
        # 스트리밍 또는 일반 생성 분기
        if "/stream" in path:
            logger.info("🌊 스트리밍 처리 시작")
            return _handle_streaming_generation(project_id, user_input, chat_history, prompt_cards, model_id)
        else:
            logger.info("📝 일반 처리 시작")
            return _handle_standard_generation(project_id, user_input, chat_history, prompt_cards, model_id)

    except json.JSONDecodeError as json_error:
        logger.error(f"❌ JSON 파싱 오류: {str(json_error)}")
        return _create_error_response(400, "잘못된 JSON 형식입니다.")
    except Exception as e:
        logger.error(f"❌ Handler 오류: {str(e)}")
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        return _create_error_response(500, f"서버 내부 오류: {e}")

def _handle_streaming_generation(project_id, user_input, chat_history, prompt_cards, model_id):
    """
    Bedrock에서 스트리밍 응답을 받아 실시간으로 반환합니다.
    청크별로 즉시 SSE 형식으로 구성하여 반환합니다.
    """
    try:
        print(f"스트리밍 생성 시작: 프로젝트 ID={project_id}, 모델={model_id}")
        final_prompt = _build_final_prompt(project_id, user_input, chat_history, prompt_cards)
        
        # 모델에 따른 요청 본문 구성
        if model_id.startswith("anthropic."):
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": final_prompt}],
                "temperature": 0.1,
                "top_p": 0.9,
            }
        else:
            # Meta Llama나 Amazon Nova 모델들을 위한 요청 형식
            request_body = {
                "prompt": final_prompt,
                "max_gen_len": 4096,
                "temperature": 0.1,
                "top_p": 0.9,
            }

        response_stream = bedrock_client.invoke_model_with_response_stream(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        
        # 최적화된 스트리밍 구현 - 버퍼링 최소화
        sse_chunks = []
        full_response = ""
        
        # 시작 이벤트
        start_data = {
            "response": "",
            "sessionId": project_id,
            "type": "start"
        }
        sse_chunks.append(f"data: {json.dumps(start_data)}\n\n")
        
        # 실시간 청크 처리 - 최소 지연
        for event in response_stream.get("body"):
            chunk = json.loads(event["chunk"]["bytes"].decode())
            
            # 모델별 응답 형식 처리
            text = None
            if model_id.startswith("anthropic."):
                # Anthropic 모델 응답 형식
                if chunk['type'] == 'content_block_delta':
                    text = chunk['delta']['text']
            else:
                # Meta Llama나 Amazon Nova 모델 응답 형식
                if 'generation' in chunk:
                    text = chunk['generation']
                elif 'text' in chunk:
                    text = chunk['text']
            
            if text:
                full_response += text
                
                # 즉시 청크 전송 (버퍼링 없음)
                sse_data = {
                    "response": text,
                    "sessionId": project_id,
                    "type": "chunk"
                }
                sse_chunks.append(f"data: {json.dumps(sse_data)}\n\n")
        
        # 완료 이벤트 전송
        completion_data = {
            "response": "",
            "sessionId": project_id,
            "type": "complete",
            "fullResponse": full_response
        }
        sse_chunks.append(f"data: {json.dumps(completion_data)}\n\n")
        
        print(f"스트리밍 생성 완료: 총 {len(sse_chunks)} 청크 생성됨, 응답 길이={len(full_response)}")
        return {
            "statusCode": 200,
            "headers": _get_sse_headers(),
            "body": "".join(sse_chunks),
            "isBase64Encoded": False
        }
                
    except Exception as e:
        print(f"스트리밍 오류: {traceback.format_exc()}")
        error_data = {
            "error": str(e),
            "sessionId": project_id,
            "type": "error"
        }
        return {
            "statusCode": 500,
            "headers": _get_sse_headers(),
            "body": f"data: {json.dumps(error_data)}\n\n",
            "isBase64Encoded": False
        }

def _handle_standard_generation(project_id, user_input, chat_history, prompt_cards, model_id):
    """일반(non-streaming) Bedrock 응답을 처리합니다."""
    try:
        print(f"일반 생성 시작: 프로젝트 ID={project_id}, 모델={model_id}")
        final_prompt = _build_final_prompt(project_id, user_input, chat_history, prompt_cards)
        
        # 모델에 따른 요청 본문 구성
        if model_id.startswith("anthropic."):
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "messages": [{"role": "user", "content": final_prompt}],
                "temperature": 0.1,
                "top_p": 0.9
            }
        else:
            # Meta Llama나 Amazon Nova 모델들을 위한 요청 형식
            request_body = {
                "prompt": final_prompt,
                "max_gen_len": 4096,
                "temperature": 0.1,
                "top_p": 0.9,
            }

        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(request_body)
        )
        response_body = json.loads(response['body'].read())
        
        # 모델별 응답 형식 처리
        if model_id.startswith("anthropic."):
            # Anthropic 모델 응답 형식
            result_text = response_body['content'][0]['text']
        else:
            # Meta Llama나 Amazon Nova 모델 응답 형식
            if 'generation' in response_body:
                result_text = response_body['generation']
            elif 'outputs' in response_body:
                result_text = response_body['outputs'][0]['text']
            else:
                result_text = response_body.get('text', str(response_body))
        
        print(f"일반 생성 완료: 응답 길이={len(result_text)}")
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"result": result_text}),
            "isBase64Encoded": False
        }
    except Exception as e:
        print(f"일반 생성 오류: {traceback.format_exc()}")
        return _create_error_response(500, f"Bedrock 호출 오류: {e}")

def _build_final_prompt(project_id, user_input, chat_history, prompt_cards):
    """프론트엔드에서 전송된 프롬프트 카드와 채팅 히스토리를 사용하여 최종 프롬프트를 구성합니다."""
    try:
        print(f"프롬프트 구성 시작: 프로젝트 ID={project_id}")
        print(f"전달받은 프롬프트 카드 수: {len(prompt_cards)}")
        print(f"전달받은 채팅 히스토리 수: {len(chat_history)}")
        
        # 프론트엔드에서 전송된 프롬프트 카드 사용 (이미 활성화된 것만 필터링되어 전송됨)
        system_prompt_parts = []
        for card in prompt_cards:
            prompt_text = card.get('prompt_text', '').strip()
            if prompt_text:
                title = card.get('title', 'Untitled')
                print(f"프롬프트 카드 적용: '{title}' ({len(prompt_text)}자)")
                system_prompt_parts.append(prompt_text)
        
        system_prompt = "\n\n".join(system_prompt_parts)
        print(f"시스템 프롬프트 길이: {len(system_prompt)}자")
        
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
        print(f"채팅 히스토리 길이: {len(history_str)}자")
        
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
        print(f"최종 프롬프트 길이: {len(final_prompt)}자")
        
        return final_prompt

    except Exception as e:
        print(f"프롬프트 구성 오류: {traceback.format_exc()}")
        # 오류 발생 시 기본 프롬프트 반환 (히스토리 포함)
        try:
            history_str = "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
            if history_str:
                return f"{history_str}\n\nHuman: {user_input}\n\nAssistant:"
            else:
                return f"Human: {user_input}\n\nAssistant:"
        except:
            return f"Human: {user_input}\n\nAssistant:"

def _get_sse_headers():
    """Server-Sent Events 응답을 위한 헤더를 반환합니다."""
    return {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Access-Control-Allow-Origin': '*',
        'X-Accel-Buffering': 'no'  # NGINX 버퍼링 비활성화
    }

def contains_recent_date_keywords(query):
    """최신 뉴스 관련 키워드를 포함하는지 확인"""
    recent_keywords = [
        '오늘', '어제', '이번주', '이번달', '최근', '지금', '현재',
        '최신', '방금', '금일', '실시간', 'today', 'recent'
    ]
    
    current_year = datetime.now().year
    year_keywords = [str(current_year), str(current_year - 1)]
    
    query_lower = query.lower()
    
    for keyword in recent_keywords + year_keywords:
        if keyword in query_lower:
            return True
    
    return False

def search_with_perplexity(query):
    """Perplexity AI를 사용한 실시간 뉴스 검색"""
    try:
        logger.info(f"Perplexity 검색 시작: {query}")
        
        url = "https://api.perplexity.ai/chat/completions"
        
        payload = {
            "model": "llama-3.1-sonar-large-128k-online",
            "messages": [
                {
                    "role": "system",
                    "content": "당신은 서울경제신문의 뉴스 어시스턴트입니다. 한국 경제 뉴스를 중심으로 정확하고 신뢰할 수 있는 정보를 제공해주세요. 답변은 한국어로 해주시고, 출처를 명시해주세요."
                },
                {
                    "role": "user", 
                    "content": f"한국 경제와 관련된 다음 질문에 답해주세요: {query}"
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.2,
            "top_p": 0.9,
            "return_citations": True,
            "search_domain_filter": ["kr"],
            "search_recency_filter": "week"
        }
        
        headers = {
            "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
            "Content-Type": "application/json"
        }
        
        logger.info("Perplexity API 호출 중...")
        
        # urllib를 사용한 HTTP 요청
        req_data = json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(url, data=req_data, headers=headers, method='POST')
        
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_data = response.read().decode('utf-8')
                data = json.loads(response_data)
                content = data['choices'][0]['message']['content']
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP Error: {e.code} - {e.reason}")
            raise Exception(f"Perplexity API HTTP Error: {e.code}")
        except urllib.error.URLError as e:
            logger.error(f"URL Error: {e.reason}")
            raise Exception(f"Perplexity API Connection Error: {e.reason}")
        
        citations = []
        if 'citations' in data:
            citations = data['citations']
        
        logger.info("Perplexity 검색 완료")
        return {
            'answer': content,
            'sources': citations,
            'search_type': 'perplexity',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Perplexity API 오류: {str(e)}")
        # Perplexity 실패 시 Knowledge Base로 폴백
        return search_knowledge_base(query)

def search_knowledge_base(query):
    """Knowledge Base를 사용한 과거 뉴스 검색"""
    try:
        logger.info(f"Knowledge Base 검색 시작: {query}")
        
        response = bedrock_agent_client.retrieve_and_generate(
            input={'text': query},
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KNOWLEDGE_BASE_ID,
                    'modelArn': f'arn:aws:bedrock:ap-northeast-2:887078546492:inference-profile/{DEFAULT_MODEL_ID}',
                    'retrievalConfiguration': {
                        'vectorSearchConfiguration': {
                            'numberOfResults': 10,
                            'overrideSearchType': 'HYBRID'
                        }
                    },
                    'generationConfiguration': {
                        'promptTemplate': {
                            'textPromptTemplate': '''당신은 서울경제신문의 뉴스 어시스턴트입니다. 
주어진 컨텍스트를 바탕으로 사용자의 질문에 정확하고 유용한 답변을 제공해주세요.

컨텍스트: $search_results$

사용자 질문: $query$

답변 시 다음 사항을 지켜주세요:
1. 한국어로 답변해주세요
2. 정확한 정보만 제공하고, 확실하지 않은 내용은 언급하지 마세요
3. 가능한 한 구체적인 날짜, 수치, 출처를 포함해주세요
4. 답변 끝에 관련 출처를 [1], [2] 형식으로 번호를 매겨 표시하고, 각 출처의 URL이 있다면 함께 제공해주세요
5. 출처 형식: [1] 기사제목 - URL (있는 경우)

답변:'''
                        }
                    }
                }
            }
        )
        
        answer = response.get('output', {}).get('text', '')
        sources = []
        
        if 'citations' in response:
            for i, citation in enumerate(response['citations'], 1):
                for reference in citation.get('retrievedReferences', []):
                    source_info = {
                        'number': i,
                        'title': reference.get('metadata', {}).get('title', ''),
                        'url': reference.get('metadata', {}).get('url', ''),
                        'date': reference.get('metadata', {}).get('date', ''),
                        'category': reference.get('metadata', {}).get('category', ''),
                        'content': reference.get('content', {}).get('text', '')[:200] + '...'
                    }
                    sources.append(source_info)
        
        logger.info("Knowledge Base 검색 완료")
        return {
            'answer': answer,
            'sources': sources,
            'search_type': 'knowledge_base',
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Knowledge Base 오류: {str(e)}")
        raise

def _handle_knowledge_base_generation(project_id, user_input, chat_history, model_id):
    """
    Smart Query Router를 활용한 조건부 분기 기반 지능형 뉴스 검색
    - 날짜 표현 감지 → 해당 기간 필터링 검색
    - 애매한 질문 → Perplexity API 우선 검색  
    - 명확한 질문 → 직접 내부 검색
    - 날짜 없음 → 최신순 우선 검색
    """
    try:
        logger.info(f"🎯 Smart Query Router 검색 시작: 프로젝트={project_id}, 질문={user_input}")
        
        # Smart Query Router 사용 (최우선)
        if SMART_ROUTER_AVAILABLE:
            return _execute_smart_router_workflow(user_input, project_id, chat_history, model_id)
        
        # Fallback 1: Enhanced Agent System
        elif ENHANCED_AGENTS_AVAILABLE:
            logger.info("Fallback: Enhanced Agent System 사용")
            return _execute_enhanced_agent_workflow(user_input, project_id, chat_history, model_id)
        
        # Fallback 2: 기존 시스템
        else:
            logger.info("Fallback: 기존 하이브리드 검색 실행")
            return _execute_legacy_workflow(user_input, project_id, chat_history, model_id)
        
    except Exception as e:
        logger.error(f"뉴스 검색 오류: {traceback.format_exc()}")
        return _create_error_response(500, f"뉴스 검색 오류: {str(e)}")


def _execute_smart_router_workflow(user_input, project_id, chat_history, model_id):
    """
    Smart Query Router 워크플로우 실행
    """
    try:
        logger.info("🎯 SmartQueryRouter 워크플로우 실행 중...")
        
        # 1. SmartQueryRouter 초기화
        logger.info("🔍 SmartQueryRouter 인스턴스 생성 시도 중...")
        try:
            smart_router = SmartQueryRouter()
            logger.info("✅ SmartQueryRouter 인스턴스 생성 성공!")
        except Exception as router_error:
            logger.error(f"❌ SmartQueryRouter 생성 실패: {str(router_error)}")
            logger.error(f"❌ 상세 오류: {traceback.format_exc()}")
            raise router_error
        
        # 2. 사용자 컨텍스트 구성
        logger.info("🔍 사용자 컨텍스트 구성 중...")
        user_context = {
            "project_id": project_id,
            "chat_history": chat_history,
            "model_id": model_id,
            "timestamp": datetime.now().isoformat()
        }
        logger.info(f"✅ 사용자 컨텍스트 구성 완료: {list(user_context.keys())}")
        
        logger.info("🚀 Smart Query Router 실행...")
        
        # 3. 메인 라우팅 및 실행
        try:
            router_result = smart_router.route_and_execute(
                query=user_input,
                context=user_context
            )
            logger.info(f"✅ Smart Query Router 실행 완료: {router_result.get('success', False)}")
        except Exception as execute_error:
            logger.error(f"❌ Smart Query Router 실행 실패: {str(execute_error)}")
            logger.error(f"❌ 상세 오류: {traceback.format_exc()}")
            raise execute_error
        
        # 4. 결과 처리
        if router_result["success"]:
            final_result = router_result["result"]
            answer = final_result.get("answer", "답변을 생성할 수 없습니다.")
            sources = final_result.get("sources", [])
            metadata = final_result.get("metadata", {})
            
            logger.info(f"✅ 답변 생성 성공: {len(answer)}자, 출처: {len(sources)}개")
            
            # 5. Smart Router 전용 응답 포맷팅
            try:
                formatted_response = _format_smart_router_response(
                    answer, sources, metadata, router_result
                )
                logger.info("✅ 응답 포맷팅 완료")
            except Exception as format_error:
                logger.error(f"❌ 응답 포맷팅 실패: {str(format_error)}")
                formatted_response = answer  # 기본 답변 사용
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({"result": formatted_response}),
                "isBase64Encoded": False
            }
        else:
            error_msg = router_result.get('error', '알 수 없는 오류')
            logger.error(f"❌ SmartQueryRouter 실행 실패: {error_msg}")
            return _create_error_response(500, f"Smart Router 오류: {error_msg}")
            
    except Exception as e:
        logger.error(f"❌ SmartQueryRouter 워크플로우 오류: {str(e)}")
        logger.error(f"❌ 상세 오류: {traceback.format_exc()}")
        return _create_error_response(500, f"Smart Router 워크플로우 오류: {str(e)}")


def _execute_enhanced_agent_workflow(user_input, project_id, chat_history, model_id):
    """
    새로운 에이전트 시스템 워크플로우 실행
    """
    try:
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
            "enable_external_search": bool(PERPLEXITY_API_KEY),
            "enable_date_intelligence": True,
            "enable_few_shot": True,
            "debug": True
        }
        
        logger.info("Enhanced Agent 워크플로우 실행 중...")
        
        # 4. 메인 워크플로우 실행
        workflow_result = execution_engine.execute_workflow(
            query=user_input,
            user_context=user_context,
            execution_options=execution_options
        )
        
        if workflow_result["success"]:
            # 성공적인 결과 처리
            final_result = workflow_result["result"]
            answer = final_result.get("answer", "답변을 생성할 수 없습니다.")
            sources = final_result.get("sources", [])
            metadata = final_result.get("metadata", {})
            
            # 프론트엔드 호환 형식으로 변환
            formatted_response = _format_enhanced_response(answer, sources, metadata, workflow_result)
            
            logger.info(f"Enhanced Agent 완료 - 실행시간: {workflow_result.get('metadata', {}).get('execution_time', 0):.2f}s")
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
                "body": json.dumps({"result": formatted_response}),
                "isBase64Encoded": False
            }
        else:
            # 실패 시 에러 응답
            error_msg = workflow_result.get("error", "알 수 없는 오류")
            logger.error(f"Enhanced Agent 실행 실패: {error_msg}")
            return _create_error_response(500, f"워크플로우 실행 실패: {error_msg}")
        
    except Exception as e:
        logger.error(f"Enhanced Agent 워크플로우 오류: {str(e)}")
        # Fallback to legacy system
        return _execute_legacy_workflow(user_input, project_id, chat_history, model_id)


def _execute_legacy_workflow(user_input, project_id, chat_history, model_id):
    """
    기존 시스템 Fallback 워크플로우
    """
    try:
        logger.info("Legacy 하이브리드 검색 실행")
        
        # 기존 로직 유지
        should_use_perplexity = contains_recent_date_keywords(user_input)
        
        if should_use_perplexity and PERPLEXITY_API_KEY:
            logger.info("Perplexity AI를 사용한 실시간 검색 실행")
            search_result = search_with_perplexity(user_input)
        else:
            logger.info("Knowledge Base를 사용한 과거 데이터 검색 실행")
            search_result = search_knowledge_base(user_input)
        
        # 응답 포맷 통일
        final_response = search_result['answer']
        
        # 출처 정보 추가
        if search_result.get('sources'):
            final_response += "\n\n**출처:**\n"
            for i, source in enumerate(search_result['sources'][:5], 1):
                if isinstance(source, dict):
                    title = source.get('title', '')
                    url = source.get('url', '')
                    if title and url:
                        final_response += f"{i}. {title} - {url}\n"
                    elif url:
                        final_response += f"{i}. {url}\n"
                elif isinstance(source, str):
                    final_response += f"{i}. {source}\n"
        
        final_response += f"\n*검색 방식: {search_result['search_type']} (Legacy)*"
        final_response += f"\n*검색 시간: {search_result['timestamp']}*"
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"result": final_response}),
            "isBase64Encoded": False
        }
        
    except Exception as e:
        logger.error(f"Legacy 워크플로우 오류: {str(e)}")
        return _create_error_response(500, f"검색 오류: {str(e)}")


def _format_smart_router_response(answer, sources, metadata, router_result):
    """
    Smart Query Router 전용 응답 포맷팅
    """
    try:
        formatted_answer = answer
        
        # 🎯 라우팅 정보 추가 (새로운 기능!)
        routing_info = router_result.get("routing_info", {})
        if routing_info:
            route_type_names = {
                "date_filtered_search": "📅 날짜 필터링 검색",
                "clarity_enhancement_flow": "❓ 명확성 향상 플로우 (Perplexity 우선)",
                "direct_internal_search": "📚 직접 내부 검색 (최신순 우선)"
            }
            route_name = route_type_names.get(routing_info.get("route_type"), routing_info.get("route_type"))
            formatted_answer += f"\n\n## 🎯 처리 방식\n"
            formatted_answer += f"**{route_name}**\n"
            formatted_answer += f"└ {routing_info.get('reason', '조건부 분기 처리')}\n"
        
        # 🧠 사고 과정 추가 (기존 기능 유지)
        thinking_process = router_result.get("thinking_process", [])
        if thinking_process:
            formatted_answer += "\n\n## 🧠 AI 사고 과정\n"
            formatted_answer += "---\n"
            for i, step in enumerate(thinking_process[:6], 1):
                step_name = step.get("step_name", f"단계 {i}")
                step_description = step.get("description", "")
                step_result = step.get("result", "")
                execution_time = step.get("execution_time", 0)
                
                formatted_answer += f"**{i}. {step_name}** ({execution_time:.1f}초)\n"
                if step_description:
                    formatted_answer += f"   └ {step_description}\n"
                if step_result and len(step_result) < 100:
                    formatted_answer += f"   → {step_result}\n"
                formatted_answer += "\n"
        
        # 📚 출처 정보 추가
        if sources:
            formatted_answer += "\n## 📚 출처\n"
            formatted_answer += "---\n"
            for i, source in enumerate(sources[:5], 1):
                title = source.get("title", "제목 없음")[:60]
                url = source.get("url", "")
                content_preview = source.get("content", "")[:100]
                
                formatted_answer += f"**[{i}] {title}**\n"
                if content_preview:
                    formatted_answer += f"   └ {content_preview}...\n"
                if url:
                    formatted_answer += f"   🔗 {url}\n"
                formatted_answer += "\n"
        
        # ⚙️ 실행 정보 추가
        execution_time = router_result.get("execution_time", 0)
        if execution_time > 0:
            formatted_answer += f"\n## ⚙️ 실행 정보\n"
            formatted_answer += f"**총 처리 시간**: {execution_time:.1f}초\n"
            formatted_answer += f"**검색된 소스**: {len(sources)}개\n"
            if routing_info.get("route_type"):
                formatted_answer += f"**라우팅 타입**: {routing_info['route_type']}\n"
        
        return formatted_answer
        
    except Exception as e:
        logger.error(f"Smart Router 응답 포맷팅 오류: {str(e)}")
        return answer or "답변 포맷팅 중 오류가 발생했습니다."


def _format_enhanced_response(answer, sources, metadata, workflow_result):
    """
    Enhanced Agent 결과를 프론트엔드 호환 형식으로 변환
    """
    try:
        formatted_answer = answer
        
        # 사고 과정 추가 (새로운 기능!)
        thinking_process = workflow_result.get("thinking_process", [])
        if thinking_process:
            formatted_answer += "\n\n## AI 사고 과정\n"
            formatted_answer += "---\n"
            for i, step in enumerate(thinking_process[:5], 1):  # 최대 5단계
                step_name = step.get("step_name", f"단계 {i}")
                step_description = step.get("description", "")
                step_result = step.get("result", "")
                execution_time = step.get("execution_time", 0)
                
                formatted_answer += f"**{i}. {step_name}** ({execution_time:.1f}초)\n"
                if step_description:
                    formatted_answer += f"   └ {step_description}\n"
                if step_result and len(step_result) < 100:  # 짧은 결과만 표시
                    formatted_answer += f"   → {step_result}\n"
                formatted_answer += "\n"
        
        # 출처 정보 추가 (기존 형식 유지)
        if sources:
            formatted_answer += "\n## 출처\n"
            formatted_answer += "---\n"
            for source in sources[:5]:  # 최대 5개
                citation_num = source.get("citation_number", 1)
                title = source.get("title", "")
                url = source.get("url", "")
                source_type = source.get("type", "unknown")
                
                if title and url:
                    formatted_answer += f"[{citation_num}] {title} - {url}\n"
                elif url:
                    formatted_answer += f"[{citation_num}] {url}\n"
                elif title:
                    formatted_answer += f"[{citation_num}] {title} ({source_type})\n"
        
        # 메타데이터 추가 (향상된 형식)
        execution_metadata = workflow_result.get("metadata", {})
        
        formatted_answer += f"\n\n##  실행 정보\n"
        formatted_answer += f"---\n"
        formatted_answer += f" **검색 방식:** Enhanced Agent System\n"
        formatted_answer += f" **실행 시간:** {execution_metadata.get('execution_time', 0):.2f}초\n"
        formatted_answer += f" **실행 단계:** {execution_metadata.get('steps_executed', 0)}개\n"
        
        if execution_metadata.get('external_search_used'):
            formatted_answer += f"🌐 **외부 검색:** Perplexity API 사용\n"
        
        formatted_answer += f" **품질 점수:** {metadata.get('quality_score', 0):.2f}/5.0\n"
        formatted_answer += f" **생성 시간:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        return formatted_answer
        
    except Exception as e:
        logger.error(f"응답 포맷팅 오류: {str(e)}")
        return f"{answer}\n\n*Enhanced Agent System (포맷팅 오류)*"

def _create_error_response(status_code, message):
    """일반적인 JSON 오류 응답을 생성합니다."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
        "body": json.dumps({"error": message, "timestamp": datetime.utcnow().isoformat()}),
        "isBase64Encoded": False
        } 
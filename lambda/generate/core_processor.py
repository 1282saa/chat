"""
서울경제신문 AI 요약 시스템 - 핵심 처리 엔진
공통 로직 중앙화로 중복 제거 및 유지보수성 향상
"""

import json
import boto3
import os
import logging
import traceback
from datetime import datetime
import sys
from pathlib import Path

# 모듈 경로 추가
sys.path.append(str(Path(__file__).parent.parent / 'date_intelligence'))
sys.path.append(str(Path(__file__).parent.parent / 'external_search'))
sys.path.append(str(Path(__file__).parent.parent / 'utils'))

try:
    from date_processor import DateIntelligenceProcessor
    from perplexity_integration import PerplexitySearchAgent
    from common_utils import DecimalEncoder
    from apac_model_manager import APACModelManager
except ImportError as e:
    logger.error(f"모듈 import 오류: {e}")

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화 (서울리전)
bedrock_runtime = boto3.client(
    service_name='bedrock-runtime',
    region_name=os.environ.get('AWS_REGION', 'ap-northeast-2')
)

bedrock_agent_runtime = boto3.client(
    service_name='bedrock-agent-runtime', 
    region_name=os.environ.get('AWS_REGION', 'ap-northeast-2')
)

s3_client = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'ap-northeast-2'))

# 환경 변수 - CDK 스택과 동일한 값들
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', 'PGQV3JXPET')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'seoul-economic-news-data-2025')
NEWS_BUCKET = os.environ.get('NEWS_BUCKET', 'seoul-economic-news-data-2025')
PERPLEXITY_API_KEY = os.environ.get('PERPLEXITY_API_KEY', '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')
AWS_REGION = os.environ.get('AWS_REGION', 'ap-northeast-2')

# APAC 모델 지원 - CDK에서 테스트된 실제 모델들
SUPPORTED_CLAUDE_MODELS = {
    "claude-3-haiku": "apac.anthropic.claude-3-haiku-20240307-v1:0",
    "claude-3-sonnet": "apac.anthropic.claude-3-sonnet-20240229-v1:0", 
    "claude-3.5-sonnet": "apac.anthropic.claude-3-5-sonnet-20240620-v1:0",
    "claude-3.5-sonnet-v2": "apac.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "claude-3.7-sonnet": "apac.anthropic.claude-3-7-sonnet-20250219-v1:0",
    "claude-4": "apac.anthropic.claude-sonnet-4-20250514-v1:0"
}

DEFAULT_MODEL_ID = "apac.anthropic.claude-3-5-sonnet-20240620-v1:0"

class NewsProcessor:
    """서울경제신문 뉴스 처리 핵심 엔진"""
    
    def __init__(self):
        """처리기 초기화 (지연 로딩 방식)"""
        self.date_processor = None
        self.perplexity_searcher = None
        self.model_manager = None
        
    def get_model_id(self, requested_model=None):
        """요청된 모델 ID 반환 (서울리전 APAC 모델 지원)"""
        if not requested_model:
            return DEFAULT_MODEL_ID
            
        # 직접 APAC 모델 ID가 전달된 경우
        if requested_model.startswith("apac.anthropic.claude"):
            return requested_model
            
        # 간단한 모델명으로 전달된 경우
        return SUPPORTED_CLAUDE_MODELS.get(requested_model, DEFAULT_MODEL_ID)
    
    def test_knowledge_base_connection(self):
        """Knowledge Base 연결 테스트"""
        try:
            if not KNOWLEDGE_BASE_ID:
                return {
                    'success': False,
                    'error': 'KNOWLEDGE_BASE_ID 환경변수가 설정되지 않았습니다.'
                }
            
            logger.info(f"🔍 Knowledge Base 연결 테스트: {KNOWLEDGE_BASE_ID}")
            
            # 간단한 테스트 쿼리 실행
            test_query = "서울경제신문 테스트"
            response = bedrock_agent_runtime.retrieve(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                retrievalQuery={'text': test_query},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': 5
                    }
                }
            )
            
            results = response.get('retrievalResults', [])
            logger.info(f"✅ Knowledge Base 연결 성공! 테스트 결과: {len(results)}개")
            
            return {
                'success': True,
                'knowledge_base_id': KNOWLEDGE_BASE_ID,
                'test_results_count': len(results),
                'region': AWS_REGION
            }
            
        except Exception as e:
            logger.error(f"❌ Knowledge Base 연결 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'knowledge_base_id': KNOWLEDGE_BASE_ID
            }
    
    def test_claude_model(self, model_tier="claude-3.5-sonnet"):
        """Claude 모델 연결 테스트"""
        try:
            model_id = self.get_model_id(model_tier)
            logger.info(f"🤖 Claude 모델 테스트: {model_id}")
            
            # 간단한 테스트 메시지
            test_prompt = "안녕하세요, 테스트입니다. 간단히 인사해주세요."
            
            # 모델별 요청 형식
            if "claude-3" in model_id:
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 1000,
                    "messages": [
                        {
                            "role": "user",
                            "content": test_prompt
                        }
                    ]
                }
            else:
                # 다른 모델 형식 (필요시)
                body = {
                    "prompt": f"\n\nHuman: {test_prompt}\n\nAssistant:",
                    "max_tokens_to_sample": 100
                }
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            
            if "claude-3" in model_id:
                result_text = response_body['content'][0]['text']
            else:
                result_text = response_body.get('completion', 'Unknown response format')
            
            logger.info(f"✅ Claude 모델 연결 성공! 응답: {result_text[:50]}...")
            
            return {
                'success': True,
                'model_id': model_id,
                'model_tier': model_tier,
                'test_response': result_text,
                'region': AWS_REGION
            }
            
        except Exception as e:
            logger.error(f"❌ Claude 모델 연결 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'model_id': model_id,
                'model_tier': model_tier
            }

    def enhance_query_with_date(self, user_input):
        """1단계: 날짜 정의 및 질문 보강"""
        try:
            # 오늘 날짜 정의
            today = datetime.now().strftime("%Y년 %m월 %d일")
            
            # 날짜 처리기 초기화 (지연 로딩)
            if not self.date_processor:
                self.date_processor = DateIntelligenceProcessor()
            
            # 자연어 날짜 표현 처리
            processed_query = self.date_processor.analyze_query_temporal_expressions(user_input)
            
            # 질문 보강 (오늘 날짜 추가)
            enhanced_query = f"오늘은 {today}입니다. {user_input}"
            
            logger.info(f"📅 날짜 보강 완료: {enhanced_query}")
            return enhanced_query
            
        except Exception as e:
            logger.error(f"❌ 날짜 처리 오류: {e}")
            # 기본 날짜 보강
            today = datetime.now().strftime("%Y년 %m월 %d일")
            return f"오늘은 {today}입니다. {user_input}"

    def search_knowledge_base(self, enhanced_query):
        """2단계: AWS 내부 지식 검색 (최신순)"""
        try:
            if not KNOWLEDGE_BASE_ID:
                logger.warning("Knowledge Base ID가 설정되지 않았습니다.")
                return "내부 지식 베이스를 사용할 수 없습니다."
            
            logger.info(f"🔍 Knowledge Base 검색 시작: {enhanced_query[:100]}...")
            
            # Bedrock Knowledge Base 검색 (최신순 정렬)
            response = bedrock_agent_runtime.retrieve(
                knowledgeBaseId=KNOWLEDGE_BASE_ID,
                retrievalQuery={'text': enhanced_query},
                retrievalConfiguration={
                    'vectorSearchConfiguration': {
                        'numberOfResults': 20  # 충분한 결과 수
                    }
                }
            )
            
            results = response.get('retrievalResults', [])
            
            if not results:
                logger.warning("Knowledge Base에서 관련 자료를 찾을 수 없습니다.")
                return "관련 뉴스 자료를 찾을 수 없습니다."
            
            # 결과를 발행일 기준으로 최신순 정렬
            sorted_results = sorted(results, 
                key=lambda x: x.get('metadata', {}).get('publish_date', ''), 
                reverse=True
            )
            
            # 상위 결과들 결합
            knowledge_text = ""
            for idx, result in enumerate(sorted_results[:10], 1):
                content = result.get('content', {}).get('text', '')
                metadata = result.get('metadata', {})
                publish_date = metadata.get('publish_date', 'Unknown')
                
                knowledge_text += f"\n[자료 {idx}] ({publish_date})\n{content}\n"
            
            logger.info(f"✅ Knowledge Base 검색 완료: {len(sorted_results)}건")
            return knowledge_text
            
        except Exception as e:
            logger.error(f"❌ Knowledge Base 검색 오류: {e}")
            return "내부 지식 검색 중 오류가 발생했습니다."

    def should_use_external_search(self, knowledge_context, user_input):
        """외부 검색 필요성 판단"""
        try:
            # 내부 검색 결과가 부족한 경우
            if len(knowledge_context) < 200:
                return True
            
            # 최신 정보가 필요한 키워드들
            recent_keywords = ['실시간', '현재', '오늘', '최신', '방금', '지금']
            if any(keyword in user_input for keyword in recent_keywords):
                return True
            
            # 특정 업종/테마 관련
            specific_keywords = ['주가', '실적', '정책', '규제', '발표', '뉴스']
            if any(keyword in user_input for keyword in specific_keywords):
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"외부 검색 판단 오류: {e}")
            return False

    def search_external_knowledge(self, enhanced_query):
        """3단계: Perplexity API로 외부 지식 보강"""
        try:
            logger.info(f"🌍 외부 검색 시작: {enhanced_query[:100]}...")
            
            # Perplexity 검색기 초기화 (지연 로딩)
            if not self.perplexity_searcher:
                self.perplexity_searcher = PerplexitySearchAgent()
            
            # 검색 실행
            search_result = self.perplexity_searcher.search_external_knowledge(enhanced_query, {})
            
            if search_result and hasattr(search_result, 'content') and search_result.content:
                logger.info(f"✅ 외부 검색 완료: {len(search_result.content)}자")
                return search_result.content
            else:
                logger.warning("외부 검색에서 결과를 찾을 수 없습니다.")
                return "외부 검색에서 추가 정보를 찾을 수 없습니다."
                
        except Exception as e:
            logger.error(f"❌ 외부 검색 오류: {e}")
            return "외부 검색 중 오류가 발생했습니다."

    def build_final_prompt(self, user_input, chat_history, knowledge_context):
        """4단계: 내부 프롬프트로 출력구조 파악 및 최종 프롬프트 구성"""
        
        # 내부 프롬프트 - 서울경제신문 AI 요약 시스템 전용
        system_prompt = """당신은 서울경제신문의 전문 AI 기자입니다. 
사용자의 질문에 대해 제공된 뉴스 자료를 바탕으로 정확하고 신뢰성 있는 답변을 제공하세요.

답변 구조:
1. 핵심 요약 (2-3문장)
2. 상세 분석 (관련 데이터 및 맥락 포함)
3. 시장/사회적 영향
4. 전망 및 의견

답변 원칙:
- 제공된 뉴스 자료를 기반으로 작성
- 정확한 수치와 날짜 인용
- 균형잡힌 시각으로 분석
- 전문적이면서도 이해하기 쉬운 설명
- 불확실한 정보는 명시
"""

        # 대화 히스토리 처리
        history_text = ""
        if chat_history:
            for msg in chat_history[-3:]:  # 최근 3개 대화만
                role = msg.get('role', '')
                content = msg.get('content', '')
                if role == 'user':
                    history_text += f"사용자: {content}\n"
                elif role == 'assistant':
                    history_text += f"AI: {content[:200]}...\n"
        
        # 최종 프롬프트 구성
        final_prompt = f"""{system_prompt}

=== 대화 맥락 ===
{history_text}

=== 관련 뉴스 자료 ===
{knowledge_context}

=== 사용자 질문 ===
{user_input}

=== AI 답변 ===
"""
        
        logger.info("📝 최종 프롬프트 구성 완료")
        return final_prompt

    def generate_with_bedrock(self, prompt, model_tier="claude-3.5-sonnet"):
        """5단계: AWS Bedrock으로 최종 생성"""
        try:
            model_id = self.get_model_id(model_tier)
            logger.info(f"🤖 Bedrock 생성 시작: {model_id}")
            
            # Claude 3 시리즈 요청 형식
            if "claude-3" in model_id:
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            else:
                # 기타 모델 (필요시)
                body = {
                    "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                    "max_tokens_to_sample": 4000,
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            
            response = bedrock_runtime.invoke_model(
                modelId=model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            
            if "claude-3" in model_id:
                generated_text = response_body['content'][0]['text']
            else:
                generated_text = response_body.get('completion', 'Generation failed')
            
            logger.info(f"✅ Bedrock 생성 완료: {len(generated_text)}자")
            return generated_text
            
        except Exception as e:
            logger.error(f"❌ Bedrock 생성 오류: {e}")
            return f"죄송합니다. 답변 생성 중 오류가 발생했습니다: {str(e)}"

    def stream_bedrock_response(self, connection_id, prompt, model_tier="claude-3.5-sonnet", send_message_func=None):
        """스트리밍 생성 (WebSocket용)"""
        try:
            model_id = self.get_model_id(model_tier)
            logger.info(f"🔄 스트리밍 생성 시작: {model_id}")
            
            if "claude-3" in model_id:
                body = {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            else:
                body = {
                    "prompt": f"\n\nHuman: {prompt}\n\nAssistant:",
                    "max_tokens_to_sample": 4000,
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            
            response = bedrock_runtime.invoke_model_with_response_stream(
                modelId=model_id,
                body=json.dumps(body)
            )
            
            # 스트리밍 처리
            full_response = ""
            for event in response['body']:
                chunk = json.loads(event['chunk']['bytes'])
                
                if "claude-3" in model_id:
                    if chunk.get('type') == 'content_block_delta':
                        delta_text = chunk.get('delta', {}).get('text', '')
                        if delta_text:
                            full_response += delta_text
                            if send_message_func:
                                send_message_func(connection_id, {
                                    'type': 'chunk',
                                    'content': delta_text
                                })
                else:
                    # 다른 모델 처리
                    if 'completion' in chunk:
                        delta_text = chunk['completion']
                        full_response += delta_text
                        if send_message_func:
                            send_message_func(connection_id, {
                                'type': 'chunk', 
                                'content': delta_text
                            })
            
            # 완료 메시지
            if send_message_func:
                send_message_func(connection_id, {
                    'type': 'complete',
                    'full_response': full_response
                })
            
            logger.info(f"✅ 스트리밍 생성 완료: {len(full_response)}자")
            return full_response
            
        except Exception as e:
            logger.error(f"❌ 스트리밍 생성 오류: {e}")
            if send_message_func:
                send_message_func(connection_id, {
                    'type': 'error',
                    'message': f"스트리밍 중 오류: {str(e)}"
                })
            return f"스트리밍 중 오류가 발생했습니다: {str(e)}"

    def process_complete_flow(self, user_input, chat_history=[], model_tier="claude-3.5-sonnet"):
        """전체 7단계 플로우 처리 (REST API용)"""
        try:
            logger.info("🚀 전체 플로우 시작")
            
            # 1-2단계: 날짜 보강
            enhanced_query = self.enhance_query_with_date(user_input)
            
            # 3-4단계: 내부 지식 검색
            knowledge_context = self.search_knowledge_base(enhanced_query)
            
            # 5단계: 외부 검색 필요성 판단 및 실행
            if self.should_use_external_search(knowledge_context, user_input):
                external_context = self.search_external_knowledge(enhanced_query)
                knowledge_context += f"\n\n=== 외부 참조 자료 ===\n{external_context}"
            
            # 6단계: 최종 프롬프트 구성
            final_prompt = self.build_final_prompt(user_input, chat_history, knowledge_context)
            
            # 7단계: Bedrock 생성
            response_content = self.generate_with_bedrock(final_prompt, model_tier)
            
            logger.info("✅ 전체 플로우 완료")
            return response_content
            
        except Exception as e:
            logger.error(f"❌ 전체 플로우 처리 오류: {e}")
            traceback.print_exc()
            return f"처리 중 오류가 발생했습니다: {str(e)}"

    def process_streaming_flow(self, connection_id, user_input, chat_history=[], model_tier="claude-3.5-sonnet", send_message_func=None):
        """전체 7단계 플로우 처리 (WebSocket 스트리밍용)"""
        try:
            logger.info("🔄 스트리밍 플로우 시작")
            
            # 상태 메시지 전송
            if send_message_func:
                send_message_func(connection_id, {
                    'type': 'status',
                    'message': '📅 날짜 정보 처리 중...'
                })
            
            # 1-2단계: 날짜 보강
            enhanced_query = self.enhance_query_with_date(user_input)
            
            if send_message_func:
                send_message_func(connection_id, {
                    'type': 'status',
                    'message': '🔍 내부 자료 검색 중...'
                })
            
            # 3-4단계: 내부 지식 검색
            knowledge_context = self.search_knowledge_base(enhanced_query)
            
            # 5단계: 외부 검색
            if self.should_use_external_search(knowledge_context, user_input):
                if send_message_func:
                    send_message_func(connection_id, {
                        'type': 'status',
                        'message': '🌍 외부 자료 검색 중...'
                    })
                
                external_context = self.search_external_knowledge(enhanced_query)
                knowledge_context += f"\n\n=== 외부 참조 자료 ===\n{external_context}"
            
            if send_message_func:
                send_message_func(connection_id, {
                    'type': 'status',
                    'message': '📝 답변 생성 중...'
                })
            
            # 6단계: 최종 프롬프트 구성
            final_prompt = self.build_final_prompt(user_input, chat_history, knowledge_context)
            
            # 7단계: 스트리밍 생성
            self.stream_bedrock_response(connection_id, final_prompt, model_tier, send_message_func)
            
            logger.info("✅ 스트리밍 플로우 완료")
            
        except Exception as e:
            logger.error(f"❌ 스트리밍 플로우 처리 오류: {e}")
            if send_message_func:
                send_message_func(connection_id, {
                    'type': 'error',
                    'message': f"처리 중 오류: {str(e)}"
                })

# 싱글톤 패턴으로 인스턴스 관리
_news_processor_instance = None

def get_news_processor():
    """NewsProcessor 싱글톤 인스턴스 반환"""
    global _news_processor_instance
    if _news_processor_instance is None:
        _news_processor_instance = NewsProcessor()
    return _news_processor_instance 
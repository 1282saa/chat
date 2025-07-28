"""
답변 합성 에이전트 (SynthesizerAgent)
- 검색 결과 종합 및 Few-shot 기반 답변 생성
- MZ세대 최적화 답변 형식
- 인용 번호 자동 삽입 및 출처 검증
- 품질 보장 및 일관성 관리
"""
import json
import os
import re
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import boto3
from dataclasses import dataclass

logger = logging.getLogger()
logger.setLevel(logging.INFO)

@dataclass
class SynthesisResult:
    """답변 합성 결과"""
    answer: str
    sources: List[Dict]
    quality_score: float
    word_count: int
    citation_count: int
    confidence: float
    metadata: Dict

class SynthesizerAgent:
    """
    검색 결과를 종합하여 최종 답변을 생성하는 에이전트
    """
    
    def __init__(self):
        # Bedrock 클라이언트
        self.bedrock_client = boto3.client("bedrock-runtime", region_name="ap-northeast-2")
        
        # APAC 지역 Claude 모델 설정 (서울 리전 최적화)
        self.apac_models = {
            "fast": "apac.anthropic.claude-3-haiku-20240307-v1:0",          # 1.89초 - 빠른 응답
            "balanced": "apac.anthropic.claude-3-sonnet-20240229-v1:0",     # 3.22초 - 균형
            "advanced": "apac.anthropic.claude-3-7-sonnet-20250219-v1:0",   # 4.17초 - 2025년 최신
            "high_performance": "apac.anthropic.claude-3-5-sonnet-20240620-v1:0",  # 3.92초 - 고성능
            "premium": "apac.anthropic.claude-sonnet-4-20250514-v1:0",      # 4.48초 - 최고급
            "latest": "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"      # 5.78초 - 최신 v2
        }
        
        # 기본 모델 설정 (환경변수로 조절 가능)
        model_tier = os.environ.get("SYNTHESIZER_MODEL_TIER", "fast")  # fast/balanced/advanced/high_performance/premium/latest
        default_model = self.apac_models.get(model_tier, self.apac_models["fast"])
        
        self.model_config = {
            "model_id": default_model,
            "max_tokens": 3000,
            "temperature": 0.3,  # 일관성 있는 답변
            "top_p": 0.9
        }
        
        # 품질 기준
        self.quality_thresholds = {
            "min_word_count": 50,
            "max_word_count": 800,
            "min_citations": 1,
            "max_citations": 10,
            "confidence_minimum": 0.7
        }
        
        # Few-shot 답변 예시들
        self.answer_examples = {
            "일반": [
                {
                    "query": "최근 경제 상황은 어떤가요?",
                    "answer": "최근 경제 상황을 분석한 결과를 말씀드리겠습니다.\n\n주요 경제 지표를 보면 [1] 관련 내용이 확인됩니다. 특히 [2] 부분에서 언급된 바와 같이 현재 상황이 나타나고 있습니다.\n\n이러한 경제 동향은 앞으로의 전망에도 영향을 미칠 것으로 예상됩니다."
                },
                {
                    "query": "기업 실적은 어떻게 되나요?",
                    "answer": "기업 실적 현황에 대해 말씀드리겠습니다.\n\n[1] 보고서에 따르면 주요 기업들의 실적이 나타나고 있습니다. [2] 데이터를 살펴보면 특정 분야에서의 성과가 두드러집니다.\n\n전반적인 기업 실적 흐름을 종합하면 현재 상황을 파악할 수 있습니다."
                }
            ],
            "정치": [
                {
                    "query": "최근 정치 동향은 어떤가요?",
                    "answer": "최근 정치 동향에 대해 말씀드리겠습니다.\n\n[1] 관련 보도에 따르면 주요 정치적 이슈들이 논의되고 있습니다. [2] 정치권에서는 이와 관련하여 다양한 입장이 표명되고 있습니다.\n\n앞으로의 정치적 전개 과정을 지켜볼 필요가 있습니다."
                },
                {
                    "query": "정부 정책 변화는 어떤가요?",
                    "answer": "정부 정책 변화에 대해 분석해드리겠습니다.\n\n[1] 발표된 정책 내용을 보면 주요 변화사항이 확인됩니다. [2] 관련 부처에서는 구체적인 실행 방안을 제시했습니다.\n\n이러한 정책 변화가 사회 각 분야에 미칠 영향을 주목할 필요가 있습니다."
                }
            ],
            "경제": [
                {
                    "query": "주식시장 동향은 어떤가요?",
                    "answer": "주식시장 동향에 대해 분석해드리겠습니다.\n\n[1] 시장 데이터를 보면 최근 주가 흐름이 나타나고 있습니다. [2] 투자자들의 관심사항과 관련하여 주요 종목들의 움직임이 확인됩니다.\n\n전체적인 시장 상황을 종합하면 현재의 투자 환경을 이해할 수 있습니다."
                }
            ]
        }
        
        logger.info(f"🤖 SynthesizerAgent 초기화 - 사용 모델: {self.model_config['model_id']}")
    
    def select_optimal_model(self, complexity_level: str = "medium", priority: str = "speed") -> str:
        """
        복잡도와 우선순위에 따른 최적 모델 선택
        
        Args:
            complexity_level: low/medium/high/expert
            priority: speed/balance/quality
        """
        
        # 복잡도별 모델 매핑
        complexity_models = {
            "low": ["fast", "balanced"],                           # 간단한 질문
            "medium": ["balanced", "high_performance"],           # 일반적인 질문
            "high": ["advanced", "high_performance", "premium"],  # 복잡한 분석 필요
            "expert": ["premium", "latest"]                       # 전문적 분석 필요
        }
        
        # 우선순위별 정렬
        priority_order = {
            "speed": ["fast", "balanced", "high_performance", "advanced", "premium", "latest"],
            "balance": ["balanced", "high_performance", "fast", "advanced", "premium", "latest"],
            "quality": ["premium", "latest", "advanced", "high_performance", "balanced", "fast"]
        }
        
        # 적절한 모델 선택
        available_models = complexity_models.get(complexity_level, ["balanced"])
        model_order = priority_order.get(priority, priority_order["balance"])
        
        # 첫 번째로 조건에 맞는 모델 선택
        for model_tier in model_order:
            if model_tier in available_models:
                selected_model = self.apac_models[model_tier]
                logger.info(f"📊 모델 선택: {model_tier} ({selected_model}) - 복잡도: {complexity_level}, 우선순위: {priority}")
                return selected_model
        
        # 기본값
        return self.model_config["model_id"]
    
    def _analyze_complexity(self, query: str, sources: List[Dict]) -> str:
        """
        질문과 소스의 복잡도 분석
        
        Returns:
            "low" / "medium" / "high" / "expert"
        """
        
        complexity_score = 0
        
        # 1. 질문 길이 및 복잡성
        if len(query) > 100:
            complexity_score += 1
        if any(keyword in query for keyword in ["분석", "비교", "전망", "예측", "평가", "상세히"]):
            complexity_score += 2
        if any(keyword in query for keyword in ["종합적으로", "심층적으로", "구체적으로", "자세히"]):
            complexity_score += 1
            
        # 2. 소스 수와 다양성
        source_count = len(sources) if sources else 0
        if source_count > 5:
            complexity_score += 2
        elif source_count > 3:
            complexity_score += 1
            
        # 3. 전문 용어 감지
        expert_keywords = ["EBITDA", "ESG", "DX", "AI", "반도체", "메타버스", "NFT", "암호화폐", "블록체인"]
        if any(keyword in query for keyword in expert_keywords):
            complexity_score += 1
            
        # 4. 수치 분석 요구
        if any(keyword in query for keyword in ["%", "억원", "조원", "달러", "증가", "감소", "상승", "하락"]):
            complexity_score += 1
            
        # 복잡도 레벨 결정
        if complexity_score >= 6:
            return "expert"
        elif complexity_score >= 4:
            return "high"
        elif complexity_score >= 2:
            return "medium"
        else:
            return "low"
        
        # Few-shot 예시 데이터베이스
        self.answer_examples = {
            "경제": [
                {
                    "query": "삼성전자 주가 동향은?",
                    "sources": "삼성전자가 3분기 실적 발표에서...(출처1), 반도체 시장 회복으로...(출처2)",
                    "answer": "삼성전자 주가는 최근 상승세를 보이고 있습니다. 3분기 실적 발표에서 메모리 반도체 사업이 예상보다 좋은 성과를 거두면서 투자자들의 관심이 높아졌습니다[1]. \n\n특히 AI용 고대역폭메모리(HBM) 수요 증가와 함께 반도체 시장 전반의 회복 신호가 나타나고 있어 향후 전망도 긍정적으로 평가되고 있습니다[2]. 다만 글로벌 경제 불확실성은 여전히 변수로 작용할 것으로 보입니다.",
                    "reason": "경제 뉴스에 대한 명확하고 간결한 답변 예시"
                },
                {
                    "query": "최근 경제 동향은?",
                    "sources": "한국은행이 기준금리를...(출처1), 물가상승률이...(출처2), 수출이...(출처3)",
                    "answer": "최근 한국 경제는 완만한 회복세를 보이고 있습니다. 한국은행이 기준금리를 동결하면서 통화정책의 안정성을 유지하고 있고[1], 물가상승률도 점차 안정화되는 모습입니다[2].\n\n수출 부문에서는 반도체와 자동차를 중심으로 개선 흐름이 나타나고 있어[3] 전반적인 경기 회복에 긍정적인 신호로 해석되고 있습니다. 다만 대외 경제 여건의 불확실성은 지속적인 관찰이 필요한 상황입니다.",
                    "reason": "종합적인 경제 상황에 대한 균형 잡힌 분석 예시"
                }
            ],
            "기업": [
                {
                    "query": "네이버 최근 소식은?",
                    "sources": "네이버가 AI 검색 서비스를...(출처1), 웹툰 사업 확장을...(출처2)",
                    "answer": "네이버는 최근 AI 기술을 활용한 새로운 검색 서비스를 선보이며 차세대 플랫폼으로의 전환을 가속화하고 있습니다[1]. 특히 생성형 AI를 접목한 개인화 검색 기능이 주목받고 있습니다.\n\n또한 글로벌 웹툰 시장에서의 입지를 더욱 강화하기 위해 해외 스튜디오 인수와 오리지널 콘텐츠 제작에 적극적으로 투자하고 있습니다[2]. 이러한 움직임은 국내를 넘어 아시아 전체로 사업 영역을 확장하려는 전략으로 분석됩니다.",
                    "reason": "기업 뉴스에 대한 전략적 관점 포함 답변 예시"
                }
            ],
            "일반": [
                {
                    "query": "오늘 주요 뉴스는?",
                    "sources": "정부가 새로운 정책을...(출처1), 날씨가...(출처2), 스포츠에서...(출처3)",
                    "answer": "오늘의 주요 뉴스를 정리해드리겠습니다.\n\n정치 분야에서는 정부가 새로운 경제 활성화 정책을 발표하며 민생 경제 지원 방안을 구체화했습니다[1]. 사회 분야에서는 전국적으로 쌀쌀한 날씨가 이어지면서 건강 관리에 주의가 당부되고 있습니다[2].\n\n스포츠 소식으로는 한국 선수들이 국제 대회에서 좋은 성과를 거두며 팬들에게 기쁨을 선사했습니다[3]. 각 분야별로 다양한 소식들이 전해지고 있어 관심 있는 영역의 상세 정보를 확인해보시길 추천드립니다.",
                    "reason": "다양한 분야의 뉴스를 체계적으로 정리한 예시"
                }
            ]
        }
        
        # MZ세대 최적화 스타일 가이드
        self.mz_style_guide = {
            "tone": "친근하면서도 정확한",
            "sentence_length": "2-3줄 내외",
            "paragraph_style": "빈 줄로 명확히 구분",
            "information_density": "핵심 정보 집중",
            "engagement": "궁금증 해소 중심",
            "forbidden": ["이모지", "특수기호(**, ##)", "과도한 수식어"]
        }
    
    def synthesize_answer(self, 
                         query: str,
                         sources: List[Dict] = None,
                         external_context: List[Dict] = None,
                         synthesis_context: Dict = None,
                         search_results: Dict = None,
                         context: Dict = None) -> SynthesisResult:
        """
        검색 결과를 종합하여 최종 답변 생성
        """
        try:
            logger.info(f"답변 합성 시작: {query}")
            logger.info(f"🔍 받은 sources 타입: {type(sources)}, 길이: {len(sources) if sources else 0}")
            
            # 새로운 파라미터 우선 처리
            if sources is not None and len(sources) > 0:
                # sources가 list로 전달된 경우 dict로 변환하여 _process_search_results 처리
                search_results_dict = {"internal_result": {"content": "", "sources": sources, "confidence": 0.7}}
                processed_sources = self._process_search_results(search_results_dict)
                logger.info(f"✅ Sources 처리 완료: {len(sources)}개")
            elif search_results is not None:
                processed_sources = self._process_search_results(search_results)
                logger.info(f"✅ Search_results 처리 완료")
            else:
                processed_sources = {"combined_content": "", "source_list": [], "source_mix": {"internal": 0, "external": 0}, "total_confidence": 0.0}
                logger.warning("⚠️ 처리할 검색 결과 없음")
            
            # external_context가 있으면 추가 처리
            if external_context:
                # external_context도 적절히 처리
                for ext_item in external_context:
                    if isinstance(ext_item, dict):
                        processed_sources["combined_content"] += f"\n외부 컨텍스트: {ext_item.get('content', '')}\n"
            
            # 2. 답변 카테고리 및 복잡도 분석
            if synthesis_context:
                category = synthesis_context.get("search_type", "일반")
            elif context:
                category = context.get("category", "일반")
            else:
                category = "일반"
            
            # 3. 질문 복잡도 분석 및 모델 선택
            complexity_level = self._analyze_complexity(query, processed_sources["source_list"])
            priority = os.environ.get("SYNTHESIS_PRIORITY", "balance")  # speed/balance/quality
            selected_model = self.select_optimal_model(complexity_level, priority)
            
            logger.info(f"답변 생성 설정: 복잡도={complexity_level}, 우선순위={priority}, 모델={selected_model}")
            
            # 4. Few-shot 예시 선택
            selected_examples = self._select_few_shot_examples(category, query)
            
            # 4. 답변 생성 프롬프트 구성
            synthesis_prompt = self._build_synthesis_prompt(
                query, processed_sources, selected_examples, context
            )
            
            # 5. Bedrock으로 답변 생성 (선택된 모델 사용)
            generated_answer = self._generate_answer_with_bedrock(synthesis_prompt, selected_model)
            
            # 6. 답변 후처리 및 검증
            final_answer = self._post_process_answer(generated_answer, processed_sources)
            
            # 7. 품질 평가
            quality_metrics = self._evaluate_answer_quality(final_answer, processed_sources, query)
            
            # 8. 인용 번호 및 출처 정리
            citation_info = self._organize_citations(final_answer, processed_sources)
            
            result = SynthesisResult(
                answer=final_answer,
                sources=citation_info["sources"],
                quality_score=quality_metrics["overall_score"],
                word_count=quality_metrics["word_count"],
                citation_count=citation_info["citation_count"],
                confidence=quality_metrics["confidence"],
                metadata={
                    "category": category,
                    "examples_used": len(selected_examples),
                    "source_mix": processed_sources["source_mix"],
                    "generation_method": "few_shot_bedrock",
                    "processing_notes": quality_metrics.get("notes", []),
                    # APAC 모델 선택 정보 추가
                    "selected_model": selected_model,
                    "complexity_level": complexity_level,
                    "model_priority": priority,
                    "model_tier": self._get_model_tier(selected_model)
                }
            )
            
            logger.info(f"답변 합성 완료 - 품질점수: {quality_metrics['overall_score']:.2f}, "
                       f"인용수: {citation_info['citation_count']}")
            
            return result
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"❌ 답변 합성 중 상세 오류: {str(e)}")
            logger.error(f"📊 오류 스택 트레이스:\n{error_details}")
            logger.error(f"🔍 디버깅 정보: sources={type(sources)}, external_context={type(external_context)}")
            return self._get_fallback_synthesis(query)
    
    def _process_search_results(self, search_results: Dict) -> Dict:
        """
        검색 결과 전처리
        """
        processed = {
            "combined_content": "",
            "source_list": [],
            "source_mix": {"internal": 0, "external": 0},
            "total_confidence": 0.0
        }
        
        # 내부 검색 결과 처리
        if search_results.get("internal_result"):
            internal = search_results["internal_result"]
            # SearchResult 객체인지 딕셔너리인지 확인 후 처리
            if hasattr(internal, 'content'):
                # SearchResult 객체인 경우
                processed["combined_content"] += f"내부 검색 결과:\n{internal.content}\n\n"
                sources = internal.sources if hasattr(internal, 'sources') else []
                confidence = internal.confidence if hasattr(internal, 'confidence') else 0.0
            else:
                # 딕셔너리인 경우 (Fallback)
                processed["combined_content"] += f"내부 검색 결과:\n{internal.get('content', '')}\n\n"
                sources = internal.get("sources", [])
                confidence = internal.get("confidence", 0.0)
            
            for i, source in enumerate(sources[:5], 1):
                # 내부 소스에 발행일 정보 포함 (뉴스 서비스 필수)
                source_item = {
                    "index": i,
                    "type": "internal",
                    "content": source.get("content", "")[:300],
                    "metadata": source.get("metadata", {}),
                    "relevance": source.get("relevance", 0.0),
                    "published_date_raw": source.get("published_date_raw", ""),
                    "published_date_korean": source.get("published_date_korean", "발행일 미상"),
                    "has_date_info": source.get("has_date_info", False)
                }
                
                processed["source_list"].append(source_item)
                processed["source_mix"]["internal"] += 1
            
            processed["total_confidence"] += confidence * 0.6
        
        # 외부 검색 결과 처리
        if search_results.get("external_result"):
            external = search_results["external_result"]
            # SearchResult 객체인지 딕셔너리인지 확인 후 처리
            if hasattr(external, 'content'):
                # SearchResult 객체인 경우
                processed["combined_content"] += f"외부 검색 결과:\n{external.content}\n\n"
                sources = external.sources if hasattr(external, 'sources') else []
                confidence = external.confidence if hasattr(external, 'confidence') else 0.0
            else:
                # 딕셔너리인 경우 (Fallback)
                processed["combined_content"] += f"외부 검색 결과:\n{external.get('content', '')}\n\n"
                sources = external.get("sources", [])
                confidence = external.get("confidence", 0.0)
            
            start_index = len(processed["source_list"]) + 1
            for i, source in enumerate(sources[:5], start_index):
                processed["source_list"].append({
                    "index": i,
                    "type": "external",
                    "title": source.get("title", ""),
                    "url": source.get("url", ""),
                    "snippet": source.get("snippet", ""),
                    "relevance": source.get("relevance", 0.0)
                })
                processed["source_mix"]["external"] += 1
            
            processed["total_confidence"] += confidence * 0.4
        
        return processed
    
    def _select_few_shot_examples(self, category: str, query: str) -> List[Dict]:
        """
        Few-shot 예시 선택
        """
        # 카테고리별 예시 선택
        category_examples = self.answer_examples.get(category, self.answer_examples["일반"])
        
        # 질문 유사성 기반 선택 (간단한 키워드 매칭)
        query_keywords = set(query.lower().split())
        
        scored_examples = []
        for example in category_examples:
            example_keywords = set(example["query"].lower().split())
            similarity = len(query_keywords & example_keywords) / len(query_keywords | example_keywords)
            scored_examples.append((similarity, example))
        
        # 상위 2개 예시 선택
        sorted_examples = sorted(scored_examples, key=lambda x: x[0], reverse=True)
        return [example for _, example in sorted_examples[:2]]
    
    def _build_synthesis_prompt(self, 
                               query: str, 
                               processed_sources: Dict, 
                               examples: List[Dict], 
                               context: Dict = None) -> str:
        """
        답변 생성 프롬프트 구성
        """
        
        # 현재 날짜 정보 생성
        from datetime import datetime
        import pytz
        
        kst = pytz.timezone('Asia/Seoul')
        current_time = datetime.now(kst)
        current_date_info = f"""
## 중요: 현재 시점 정보
- 오늘 날짜: {current_time.strftime('%Y년 %m월 %d일')} ({current_time.strftime('%A')})
- 현재 년도: {current_time.year}년
- 1년 전: {current_time.year - 1}년
- 2년 전: {current_time.year - 2}년
- 작년: {current_time.year - 1}년

⚠️ 중요: 위 정보를 바탕으로 날짜 관련 질문에 정확히 답변하세요.
"""
        
        # Few-shot 예시 구성
        example_text = ""
        for i, example in enumerate(examples, 1):
            # sources 키가 있으면 사용하고, 없으면 기본값 사용
            example_sources = example.get('sources', '관련 뉴스 기사 및 분석 자료')
            example_text += f"""
예시 {i}:
질문: {example['query']}
주어진 정보: {example_sources}
답변: {example['answer']}

"""
        
        # 메인 프롬프트
        prompt = f"""당신은 서울경제신문의 전문 뉴스 분석가입니다. 주어진 검색 결과를 바탕으로 사용자의 질문에 대해 정확하고 읽기 쉬운 답변을 작성해주세요.

{current_date_info}

## 📰 뉴스 서비스 필수 규칙 (반드시 준수)

**날짜 정보 필수 포함:**
- 모든 사실에 구체적인 날짜 명시 (년/월/일/시간)
- "최신", "최근", "며칠 전" 같은 애매한 표현 금지
- 예: "2025년 7월 28일 오후 2시 발표", "7월 27일 오전 10시 30분 공시"
- S3 메타데이터의 발행일 정보 반드시 활용

**출처별 발행 시점 명시:**
- 각 출처의 정확한 발행일시 포함
- 예: "[1] 2025년 7월 28일 14:30 - 삼성전자 실적 발표"
- 예: "[2] 7월 27일 오후 3시 - 하이닉스 주가 급등 소식"

**정확성 우선:**
- 발행일이 불명확한 정보는 "발행일 미상" 명시
- 추정 정보는 "추정" 또는 "예상" 명시
- 과거 사실은 정확한 과거 날짜로 표기

## 답변 작성 규칙

**스타일 가이드:**
- MZ세대가 읽기 쉬운 친근하면서도 정확한 톤
- 문장은 2-3줄 내외로 간결하게
- 문단은 빈 줄로 명확히 구분
- 핵심 정보에 집중하여 궁금증 해소
- 이모지나 특수기호(**, ##) 사용 금지

**인용 규칙:**
- 반드시 출처 정보를 [숫자] 형식으로 표시
- 각 주요 정보마다 해당하는 출처 번호 삽입
- 인용 번호는 문장 끝에 배치
- 출처에 발행일시 포함

**내용 구성:**
- 50-800단어 내외로 작성
- 객관적 사실 중심으로 서술
- 추측이나 개인 의견 배제
- 구체적인 날짜, 수치, 인명, 기관명 포함

## Few-shot 학습 예시

{example_text}

## 실제 작업

질문: {query}

주어진 검색 결과:
{processed_sources['combined_content']}

출처 목록:
{self._format_source_list(processed_sources['source_list'])}

위 정보를 바탕으로 질문에 대한 답변을 작성해주세요. 반드시 인용 번호를 포함하고, MZ세대가 읽기 쉬운 형식으로 작성해주세요."""

        return prompt
    
    def _get_model_tier(self, model_id: str) -> str:
        """모델 ID에서 tier 이름 추출"""
        for tier, tier_model_id in self.apac_models.items():
            if tier_model_id == model_id:
                return tier
        return "unknown"
    
    def _format_source_list(self, source_list: List[Dict]) -> str:
        """출처 목록 포맷팅 (뉴스 서비스용 - 발행일 정보 포함)"""
        formatted_sources = []
        
        for source in source_list:
            if source["type"] == "internal":
                # 내부 소스의 발행일 정보 포함
                published_date = source.get('published_date_korean', '')
                date_info = f" ({published_date})" if published_date and published_date != "발행일 미상" else " (발행일 미상)"
                
                formatted_sources.append(
                    f"[{source['index']}] 내부 문서{date_info}: {source['content'][:100]}..."
                )
            else:
                # 외부 소스 (Perplexity 등)
                title = source.get('title', 'External Source')
                snippet = source.get('snippet', '')[:100]
                domain = source.get('domain', '')
                
                # 외부 소스도 가능하면 날짜 정보 포함
                if domain:
                    formatted_sources.append(
                        f"[{source['index']}] {title} ({domain}): {snippet}..."
                    )
                else:
                    formatted_sources.append(
                        f"[{source['index']}] {title}: {snippet}..."
                    )
        
        return "\n".join(formatted_sources)
    
    def _generate_answer_with_bedrock(self, prompt: str, model_id: str = None) -> str:
        """
        Bedrock을 사용한 답변 생성 (동적 모델 선택 지원)
        
        Args:
            prompt: 생성할 프롬프트
            model_id: 사용할 모델 ID (None이면 기본 설정 사용)
        """
        try:
            # 사용할 모델 결정
            selected_model = model_id or self.model_config["model_id"]
            
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.model_config["max_tokens"],
                "temperature": self.model_config["temperature"],
                "top_p": self.model_config["top_p"],
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            logger.info(f"🚀 답변 생성 시작: {selected_model}")
            
            response = self.bedrock_client.invoke_model(
                modelId=selected_model,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            generated_text = response_body['content'][0]['text']
            
            logger.info(f"✅ 답변 생성 완료: {len(generated_text)}자")
            
            return generated_text.strip()
            
        except Exception as e:
            logger.error(f"❌ Bedrock 답변 생성 오류 (모델: {selected_model}): {str(e)}")
            
            # 폴백: 기본 모델로 재시도
            if model_id and model_id != self.model_config["model_id"]:
                logger.info(f"🔄 기본 모델로 재시도: {self.model_config['model_id']}")
                return self._generate_answer_with_bedrock(prompt, self.model_config["model_id"])
            
            return "답변 생성 중 오류가 발생했습니다. 나중에 다시 시도해 주세요."
    
    def _post_process_answer(self, raw_answer: str, processed_sources: Dict) -> str:
        """
        답변 후처리
        """
        processed_answer = raw_answer
        
        # 1. 불필요한 접두사 제거
        processed_answer = re.sub(r'^답변:\s*', '', processed_answer)
        processed_answer = re.sub(r'^Answer:\s*', '', processed_answer)
        
        # 2. 과도한 줄바꿈 정리
        processed_answer = re.sub(r'\n{3,}', '\n\n', processed_answer)
        
        # 3. 특수기호 제거
        processed_answer = re.sub(r'\*\*([^*]+)\*\*', r'\1', processed_answer)  # **굵게** 제거
        processed_answer = re.sub(r'##\s*([^\n]+)', r'\1', processed_answer)    # ## 제목 제거
        processed_answer = re.sub(r'[📖📊📈📉💡🔍]', '', processed_answer)    # 이모지 제거
        
        # 4. 인용 번호 검증 및 정리
        processed_answer = self._validate_citations(processed_answer, len(processed_sources["source_list"]))
        
        # 5. 문단 정리
        processed_answer = self._format_paragraphs(processed_answer)
        
        return processed_answer.strip()
    
    def _validate_citations(self, answer: str, source_count: int) -> str:
        """
        인용 번호 검증 및 정리
        """
        # 존재하지 않는 인용 번호 제거
        def replace_invalid_citation(match):
            citation_num = int(match.group(1))
            if 1 <= citation_num <= source_count:
                return match.group(0)
            else:
                return ""
        
        # [숫자] 형식의 인용 번호 검증
        validated_answer = re.sub(r'\[(\d+)\]', replace_invalid_citation, answer)
        
        # 인용 번호가 하나도 없으면 기본 인용 추가
        if not re.search(r'\[\d+\]', validated_answer) and source_count > 0:
            validated_answer += "[1]"
        
        return validated_answer
    
    def _format_paragraphs(self, answer: str) -> str:
        """
        문단 형식 정리
        """
        # 문장 끝의 인용 번호 뒤에 적절한 간격 보장
        formatted = re.sub(r'(\[\d+\])([가-힣a-zA-Z])', r'\1 \2', answer)
        
        # 문단 구분 정리
        paragraphs = formatted.split('\n\n')
        clean_paragraphs = []
        
        for para in paragraphs:
            clean_para = para.strip()
            if clean_para:
                clean_paragraphs.append(clean_para)
        
        return '\n\n'.join(clean_paragraphs)
    
    def _evaluate_answer_quality(self, answer: str, processed_sources: Dict, query: str) -> Dict:
        """
        답변 품질 평가
        """
        metrics = {
            "word_count": len(answer.split()),
            "citation_count": len(re.findall(r'\[\d+\]', answer)),
            "paragraph_count": len(answer.split('\n\n')),
            "confidence": 0.5,  # 기본값
            "overall_score": 0.5,
            "notes": []
        }
        
        # 길이 평가
        word_count = metrics["word_count"]
        if self.quality_thresholds["min_word_count"] <= word_count <= self.quality_thresholds["max_word_count"]:
            metrics["confidence"] += 0.2
        elif word_count < self.quality_thresholds["min_word_count"]:
            metrics["notes"].append("답변이 너무 짧음")
        elif word_count > self.quality_thresholds["max_word_count"]:
            metrics["notes"].append("답변이 너무 김")
        
        # 인용 평가
        citation_count = metrics["citation_count"]
        if self.quality_thresholds["min_citations"] <= citation_count <= self.quality_thresholds["max_citations"]:
            metrics["confidence"] += 0.2
        elif citation_count == 0:
            metrics["notes"].append("인용 없음")
        
        # 내용 품질 평가
        if any(keyword in answer.lower() for keyword in ["분석", "전망", "발표", "보도"]):
            metrics["confidence"] += 0.1
        
        # 구조 평가
        if metrics["paragraph_count"] >= 2:
            metrics["confidence"] += 0.1  # 적절한 문단 구성
        
        # 전체 점수 계산
        metrics["overall_score"] = min(metrics["confidence"], 1.0)
        
        return metrics
    
    def _organize_citations(self, answer: str, processed_sources: Dict) -> Dict:
        """
        인용 정보 정리
        """
        citation_numbers = re.findall(r'\[(\d+)\]', answer)
        unique_citations = list(set(map(int, citation_numbers)))
        
        organized_sources = []
        for citation_num in sorted(unique_citations):
            if citation_num <= len(processed_sources["source_list"]):
                source = processed_sources["source_list"][citation_num - 1]
                organized_sources.append({
                    "citation_number": citation_num,
                    "type": source["type"],
                    "title": source.get("title", f"출처 {citation_num}"),
                    "url": source.get("url", ""),
                    "snippet": source.get("snippet", source.get("content", ""))[:200]
                })
        
        return {
            "sources": organized_sources,
            "citation_count": len(unique_citations),
            "coverage": len(unique_citations) / len(processed_sources["source_list"]) if processed_sources["source_list"] else 0.0
        }
    
    def _get_fallback_synthesis(self, query: str) -> SynthesisResult:
        """Fallback 답변 합성"""
        fallback_answer = f"죄송합니다. '{query}'에 대한 답변을 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
        
        return SynthesisResult(
            answer=fallback_answer,
            sources=[],
            quality_score=0.0,
            word_count=len(fallback_answer.split()),
            citation_count=0,
            confidence=0.0,
            metadata={"fallback": True, "error": "synthesis_failed"}
        )
    
    def to_dict(self, synthesis_result: SynthesisResult) -> Dict:
        """SynthesisResult를 딕셔너리로 변환"""
        return {
            "answer": synthesis_result.answer,
            "sources": synthesis_result.sources,
            "quality_score": synthesis_result.quality_score,
            "word_count": synthesis_result.word_count,
            "citation_count": synthesis_result.citation_count,
            "confidence": synthesis_result.confidence,
            "metadata": synthesis_result.metadata
        }

# 사용 예시
if __name__ == "__main__":
    synthesizer = SynthesizerAgent()
    
    # 테스트 검색 결과 (Mock)
    test_search_results = {
        "internal_result": {
            "content": "삼성전자가 3분기 실적에서 메모리 반도체 부문이 예상보다 좋은 성과를 보였다고 발표했습니다.",
            "sources": [
                {
                    "content": "삼성전자 3분기 메모리 반도체 실적 개선",
                    "metadata": {"published_date": "2024-10-25"},
                    "relevance": 0.9
                }
            ],
            "confidence": 0.8
        },
        "external_result": {
            "content": "AI 반도체 수요 증가로 삼성전자 주가가 상승세를 보이고 있습니다.",
            "sources": [
                {
                    "title": "삼성전자 주가 상승",
                    "url": "https://example.com/news1",
                    "snippet": "AI 반도체 수요 증가로 주가 상승"
                }
            ],
            "confidence": 0.7
        }
    }
    
    # 테스트 쿼리들
    test_queries = [
        {
            "query": "삼성전자 최근 실적은?",
            "context": {"category": "기업"}
        },
        {
            "query": "경제 동향은?",
            "context": {"category": "경제"}
        }
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"테스트 {i}: {test_case['query']}")
        print('='*80)
        
        result = synthesizer.synthesize_answer(
            test_case["query"],
            test_search_results,
            test_case.get("context")
        )
        
        result_dict = synthesizer.to_dict(result)
        print(json.dumps(result_dict, ensure_ascii=False, indent=2))
    
    print(f"\n{'='*80}")
    print("SynthesizerAgent 테스트 완료!")
    print('='*80) 
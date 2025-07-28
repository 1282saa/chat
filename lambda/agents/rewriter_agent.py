"""
질문 재구성 에이전트 (RewriterAgent)
- 애매한 질문을 구체적으로 재작성
- 검색 최적화를 위한 쿼리 개선
- 재질문 인터랙션 처리
- Few-shot 예시 기반 질문 개선
"""
import json
import re
import logging
from typing import Dict, List, Any, Optional
import boto3
from dataclasses import dataclass

logger = logging.getLogger()
logger.setLevel(logging.INFO)

@dataclass
class RewriteResult:
    """재작성 결과 데이터 클래스"""
    original_query: str
    rewritten_queries: List[Dict]
    confidence: float
    improvement_type: str
    clarification_questions: List[str]
    needs_user_input: bool

class RewriterAgent:
    """
    애매한 질문을 구체화하는 질문 재구성 에이전트
    """
    
    def __init__(self):
        # Bedrock 클라이언트
        self.bedrock_client = boto3.client("bedrock-runtime", region_name="ap-northeast-2")
        
        # 임계값 설정
        self.thresholds = {
            "clarity_minimum": 0.8,      # 재작성 필요 기준
            "confidence_minimum": 0.75,  # 재작성 결과 신뢰도
            "max_alternatives": 3        # 최대 대안 질문 수
        }
        
        # Few-shot 예시 데이터베이스
        self.rewrite_examples = {
            "vague_to_specific": [
                {
                    "original": "삼성전자?",
                    "rewritten": [
                        "삼성전자 최근 주가 동향은 어떤가요?",
                        "삼성전자 2024년 실적은 어떻게 되나요?",
                        "삼성전자 반도체 사업 현황이 궁금합니다"
                    ],
                    "reason": "기업명만 있는 경우 구체적인 정보 요청으로 확장"
                },
                {
                    "original": "반도체",
                    "rewritten": [
                        "한국 반도체 시장 최근 동향은?",
                        "반도체 주요 기업들의 실적은?",
                        "반도체 산업 전망은 어떤가요?"
                    ],
                    "reason": "산업명만 있는 경우 구체적인 관점 추가"
                },
                {
                    "original": "경제",
                    "rewritten": [
                        "최근 한국 경제 동향은?",
                        "2024년 경제 전망은?",
                        "현재 경제 주요 이슈는?"
                    ],
                    "reason": "일반적인 주제를 구체적인 질문으로 세분화"
                }
            ],
            "add_context": [
                {
                    "original": "주가가 어떤가요?",
                    "rewritten": [
                        "어떤 기업의 주가가 궁금하신가요?",
                        "특정 종목의 주가 동향을 원하시나요?",
                        "전체 증시 동향을 말씀하시는 건가요?"
                    ],
                    "reason": "대상이 불명확한 경우 구체화 필요"
                }
            ],
            "add_timeframe": [
                {
                    "original": "실적이 어떤가요?",
                    "rewritten": [
                        "최근 실적이 궁금하신가요?",
                        "특정 분기 실적을 원하시나요?",
                        "전년 대비 실적 비교를 원하시나요?"
                    ],
                    "reason": "시간 범위 불명확한 경우 시점 구체화"
                }
            ]
        }
        
        # 질문 패턴 분류
        self.question_patterns = {
            "single_word": r'^[가-힣a-zA-Z]+\??$',
            "company_only": r'^[가-힣a-zA-Z]+[전자|그룹|회사]?\??$',
            "what_without_subject": r'^[무엇|뭐|어떤].*\??$',
            "how_without_context": r'^어떻게.*\??$',
            "vague_inquiry": r'^.*어떤가요?\??$|^.*어때요?\??$'
        }
        
        # 검색 최적화 키워드
        self.search_enhancers = {
            "경제": ["경제뉴스", "경제동향", "시장분석"],
            "기업": ["기업소식", "회사뉴스", "비즈니스"],
            "주가": ["주식", "증시", "투자"],
            "실적": ["재무실적", "영업실적", "매출"],
            "전망": ["전망분석", "예측", "향후계획"]
        }
    
    def rewrite_query(self, 
                     original_query: str, 
                     analysis_context: Dict = None,
                     user_feedback: str = None) -> RewriteResult:
        """
        질문 재작성 메인 함수
        """
        try:
            logger.info(f"질문 재작성 시작: {original_query}")
            
            # 1. 질문 패턴 분석
            pattern_type = self._identify_question_pattern(original_query)
            
            # 2. 재작성 전략 선택
            strategy = self._select_rewrite_strategy(pattern_type, analysis_context)
            
            # 3. Few-shot 기반 재작성 실행
            if user_feedback:
                # 사용자 피드백이 있는 경우 대화형 재작성
                rewrite_result = self._interactive_rewrite(original_query, user_feedback, analysis_context)
            else:
                # 자동 재작성
                rewrite_result = self._automatic_rewrite(original_query, strategy, analysis_context)
            
            # 4. 검색 최적화 적용
            optimized_queries = self._optimize_for_search(rewrite_result["queries"], analysis_context)
            
            # 5. 품질 평가
            confidence = self._evaluate_rewrite_quality(original_query, optimized_queries)
            
            # 6. 재질문 생성 (필요한 경우)
            clarification_questions = []
            needs_user_input = False
            
            if confidence < self.thresholds["confidence_minimum"]:
                clarification_questions = self._generate_clarification_questions(
                    original_query, pattern_type, analysis_context
                )
                needs_user_input = len(clarification_questions) > 0
            
            result = RewriteResult(
                original_query=original_query,
                rewritten_queries=optimized_queries,
                confidence=confidence,
                improvement_type=strategy,
                clarification_questions=clarification_questions,
                needs_user_input=needs_user_input
            )
            
            logger.info(f"재작성 완료 - 전략: {strategy}, 신뢰도: {confidence:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"질문 재작성 중 오류: {str(e)}")
            return self._get_fallback_result(original_query)
    
    def _identify_question_pattern(self, query: str) -> str:
        """질문 패턴 식별"""
        for pattern_name, pattern_regex in self.question_patterns.items():
            if re.match(pattern_regex, query.strip(), re.IGNORECASE):
                return pattern_name
        
        # 길이 기반 분류
        if len(query.strip()) < 5:
            return "too_short"
        elif len(query.split()) == 1:
            return "single_word"
        elif "?" not in query and len(query.split()) < 3:
            return "incomplete"
        else:
            return "needs_clarification"
    
    def _select_rewrite_strategy(self, pattern_type: str, context: Dict = None) -> str:
        """재작성 전략 선택"""
        
        if pattern_type in ["single_word", "company_only"]:
            return "expand_with_context"
        elif pattern_type in ["what_without_subject", "how_without_context"]:
            return "add_specific_subject"
        elif pattern_type == "vague_inquiry":
            return "specify_information_type"
        elif pattern_type == "too_short":
            return "request_elaboration"
        elif pattern_type == "incomplete":
            return "complete_question"
        else:
            return "general_improvement"
    
    def _automatic_rewrite(self, query: str, strategy: str, context: Dict = None) -> Dict:
        """자동 재작성"""
        
        rewritten_queries = []
        
        if strategy == "expand_with_context":
            rewritten_queries = self._expand_with_context(query, context)
        elif strategy == "add_specific_subject":
            rewritten_queries = self._add_specific_subject(query, context)
        elif strategy == "specify_information_type":
            rewritten_queries = self._specify_information_type(query, context)
        elif strategy == "complete_question":
            rewritten_queries = self._complete_question(query, context)
        else:
            rewritten_queries = self._general_improvement(query, context)
        
        return {
            "queries": rewritten_queries,
            "strategy": strategy,
            "automatic": True
        }
    
    def _expand_with_context(self, query: str, context: Dict = None) -> List[Dict]:
        """맥락을 추가하여 확장"""
        base_term = query.strip().rstrip('?')
        
        # 기업명인지 확인
        if any(keyword in base_term for keyword in ["전자", "그룹", "회사", "코퍼레이션"]):
            return [
                {
                    "query": f"{base_term} 최근 주가 동향은?",
                    "priority": 1,
                    "reason": "주가 정보 요청으로 구체화",
                    "search_type": "latest_first"
                },
                {
                    "query": f"{base_term} 2024년 실적은?",
                    "priority": 2,
                    "reason": "실적 정보 요청으로 구체화",
                    "search_type": "date_filtered"
                },
                {
                    "query": f"{base_term} 최신 뉴스는?",
                    "priority": 3,
                    "reason": "일반 뉴스 요청으로 구체화",
                    "search_type": "latest_first"
                }
            ]
        
        # 산업/분야명인지 확인
        elif any(keyword in base_term for keyword in ["반도체", "자동차", "바이오", "금융"]):
            return [
                {
                    "query": f"{base_term} 시장 최근 동향은?",
                    "priority": 1,
                    "reason": "시장 동향으로 구체화",
                    "search_type": "latest_first"
                },
                {
                    "query": f"{base_term} 주요 기업 현황은?",
                    "priority": 2,
                    "reason": "기업 현황으로 구체화",
                    "search_type": "latest_first"
                },
                {
                    "query": f"{base_term} 산업 전망은?",
                    "priority": 3,
                    "reason": "산업 전망으로 구체화",
                    "search_type": "multi_source"
                }
            ]
        
        # 기본 확장
        else:
            return [
                {
                    "query": f"{base_term}에 대한 최신 정보는?",
                    "priority": 1,
                    "reason": "일반적 정보 요청으로 구체화",
                    "search_type": "latest_first"
                },
                {
                    "query": f"{base_term} 관련 뉴스는?",
                    "priority": 2,
                    "reason": "뉴스 요청으로 구체화",
                    "search_type": "latest_first"
                }
            ]
    
    def _add_specific_subject(self, query: str, context: Dict = None) -> List[Dict]:
        """구체적인 주체 추가"""
        
        # 카테고리 정보 활용
        category = context.get("category", "일반") if context else "일반"
        
        if "무엇" in query or "뭐" in query:
            if category == "경제":
                return [
                    {
                        "query": "최근 주요 경제 이슈는 무엇인가요?",
                        "priority": 1,
                        "reason": "경제 이슈로 구체화",
                        "search_type": "latest_first"
                    },
                    {
                        "query": "현재 경제 동향에서 주목할 점은?",
                        "priority": 2,
                        "reason": "경제 동향으로 구체화",
                        "search_type": "latest_first"
                    }
                ]
            elif category == "기업":
                return [
                    {
                        "query": "주요 기업들의 최근 소식은?",
                        "priority": 1,
                        "reason": "기업 소식으로 구체화",
                        "search_type": "latest_first"
                    }
                ]
        
        # 기본 구체화
        return [
            {
                "query": f"구체적으로 어떤 정보를 원하시나요? ({query})",
                "priority": 1,
                "reason": "재질문으로 구체화 유도",
                "search_type": "clarification"
            }
        ]
    
    def _specify_information_type(self, query: str, context: Dict = None) -> List[Dict]:
        """정보 유형 구체화"""
        
        # "어떤가요", "어때요" 패턴 처리
        base_query = re.sub(r'어떤가요\??|어때요\??', '', query).strip()
        
        if not base_query:
            return [
                {
                    "query": "구체적으로 어떤 정보가 필요하신가요?",
                    "priority": 1,
                    "reason": "정보 유형 확인 필요",
                    "search_type": "clarification"
                }
            ]
        
        return [
            {
                "query": f"{base_query} 최신 동향은?",
                "priority": 1,
                "reason": "동향 정보로 구체화",
                "search_type": "latest_first"
            },
            {
                "query": f"{base_query} 현재 상황은?",
                "priority": 2,
                "reason": "현황 정보로 구체화",
                "search_type": "latest_first"
            },
            {
                "query": f"{base_query} 관련 분석은?",
                "priority": 3,
                "reason": "분석 정보로 구체화",
                "search_type": "multi_source"
            }
        ]
    
    def _complete_question(self, query: str, context: Dict = None) -> List[Dict]:
        """불완전한 질문 완성"""
        
        # 맥락 정보 활용
        entities = context.get("entities", {}) if context else {}
        companies = entities.get("companies", [])
        
        completed_queries = []
        
        if companies:
            # 기업명이 있는 경우
            for company in companies[:2]:  # 최대 2개 기업
                completed_queries.append({
                    "query": f"{company} {query} 관련 최신 정보는?",
                    "priority": len(completed_queries) + 1,
                    "reason": f"{company} 관련 정보로 완성",
                    "search_type": "latest_first"
                })
        
        # 기본 완성
        if not completed_queries:
            completed_queries.append({
                "query": f"{query}에 대한 상세한 정보를 알려주세요",
                "priority": 1,
                "reason": "일반적 완성",
                "search_type": "latest_first"
            })
        
        return completed_queries
    
    def _general_improvement(self, query: str, context: Dict = None) -> List[Dict]:
        """일반적인 개선"""
        
        # 검색 키워드 추가
        improved_query = query
        
        # 맥락 기반 키워드 추가
        category = context.get("category", "") if context else ""
        if category in self.search_enhancers:
            keywords = self.search_enhancers[category]
            improved_query += f" {keywords[0]}"
        
        return [
            {
                "query": improved_query,
                "priority": 1,
                "reason": "검색 키워드 추가로 개선",
                "search_type": "latest_first"
            },
            {
                "query": f"{query} 자세히",
                "priority": 2,
                "reason": "상세 정보 요청으로 개선",
                "search_type": "multi_source"
            }
        ]
    
    def _interactive_rewrite(self, query: str, user_feedback: str, context: Dict = None) -> Dict:
        """대화형 재작성"""
        
        # 사용자 피드백 분석
        if any(word in user_feedback for word in ["주가", "stock", "price"]):
            focus = "주가"
        elif any(word in user_feedback for word in ["실적", "performance", "earnings"]):
            focus = "실적"
        elif any(word in user_feedback for word in ["뉴스", "news", "소식"]):
            focus = "뉴스"
        else:
            focus = "일반"
        
        # 피드백 기반 재작성
        base_query = query.strip()
        
        rewritten_queries = [
            {
                "query": f"{base_query} {focus} 정보",
                "priority": 1,
                "reason": f"사용자 피드백 '{user_feedback}' 반영",
                "search_type": "latest_first"
            }
        ]
        
        return {
            "queries": rewritten_queries,
            "strategy": "user_feedback_based",
            "automatic": False,
            "feedback_applied": user_feedback
        }
    
    def _optimize_for_search(self, queries: List[Dict], context: Dict = None) -> List[Dict]:
        """검색 최적화"""
        
        optimized = []
        
        for query_info in queries:
            original_query = query_info["query"]
            
            # 검색 키워드 강화
            enhanced_query = self._enhance_search_keywords(original_query, context)
            
            # 최적화된 정보 업데이트
            optimized_info = query_info.copy()
            optimized_info["query"] = enhanced_query
            optimized_info["original_query"] = original_query
            optimized_info["optimized"] = True
            
            optimized.append(optimized_info)
        
        return optimized
    
    def _enhance_search_keywords(self, query: str, context: Dict = None) -> str:
        """검색 키워드 강화"""
        
        enhanced_query = query
        
        # 뉴스 관련 키워드 추가
        if not any(news_word in query for news_word in ["뉴스", "소식", "기사"]):
            enhanced_query += " 뉴스"
        
        # 한국 관련 키워드 추가 (해외 기업이 아닌 경우)
        if context and context.get("category") in ["경제", "기업"]:
            entities = context.get("entities", {})
            companies = entities.get("companies", [])
            
            # 한국 기업인 경우 한국 키워드 추가
            korean_companies = ["삼성", "LG", "현대", "SK", "네이버", "카카오"]
            if any(korean_comp in comp for korean_comp in korean_companies for comp in companies):
                if "한국" not in enhanced_query:
                    enhanced_query = f"한국 {enhanced_query}"
        
        return enhanced_query
    
    def _evaluate_rewrite_quality(self, original: str, rewritten_queries: List[Dict]) -> float:
        """재작성 품질 평가"""
        
        if not rewritten_queries:
            return 0.0
        
        quality_score = 0.5  # 기본 점수
        
        # 길이 개선 평가
        avg_length = sum(len(q["query"]) for q in rewritten_queries) / len(rewritten_queries)
        if avg_length > len(original) * 1.5:
            quality_score += 0.2
        
        # 구체성 개선 평가
        original_specificity = len(original.split())
        avg_specificity = sum(len(q["query"].split()) for q in rewritten_queries) / len(rewritten_queries)
        if avg_specificity > original_specificity * 1.3:
            quality_score += 0.2
        
        # 다양성 평가
        if len(rewritten_queries) >= 2:
            quality_score += 0.1
        
        return min(quality_score, 1.0)
    
    def _generate_clarification_questions(self, query: str, pattern_type: str, context: Dict = None) -> List[str]:
        """재질문 생성"""
        
        questions = []
        
        if pattern_type == "single_word":
            questions.extend([
                f"'{query}'에 대해 구체적으로 어떤 정보가 필요하신가요?",
                "최신 동향, 실적, 또는 뉴스 중 어떤 것을 원하시나요?",
                "특정 시점이나 기간의 정보를 원하시나요?"
            ])
        
        elif pattern_type == "company_only":
            questions.extend([
                "해당 기업의 어떤 측면이 궁금하신가요? (주가, 실적, 뉴스 등)",
                "최근 정보를 원하시나요, 아니면 특정 시점의 정보를 원하시나요?",
                "구체적으로 어떤 정보가 필요하신지 말씀해 주세요"
            ])
        
        elif pattern_type == "vague_inquiry":
            questions.extend([
                "더 구체적으로 어떤 정보를 원하시는지 설명해 주세요",
                "관심 있는 특정 측면이나 분야가 있나요?",
                "어떤 시점의 정보가 필요하신가요?"
            ])
        
        else:
            questions.extend([
                "질문을 좀 더 구체적으로 말씀해 주실 수 있나요?",
                "어떤 종류의 정보를 찾고 계신가요?",
                "관련된 구체적인 키워드나 회사명이 있나요?"
            ])
        
        return questions[:3]  # 최대 3개
    
    def _get_fallback_result(self, query: str) -> RewriteResult:
        """Fallback 재작성 결과"""
        return RewriteResult(
            original_query=query,
            rewritten_queries=[
                {
                    "query": f"{query} 관련 최신 정보",
                    "priority": 1,
                    "reason": "기본 재작성",
                    "search_type": "latest_first",
                    "optimized": False
                }
            ],
            confidence=0.5,
            improvement_type="fallback",
            clarification_questions=[
                "더 구체적인 정보가 필요하시다면 말씀해 주세요"
            ],
            needs_user_input=True
        )
    
    def to_dict(self, rewrite_result: RewriteResult) -> Dict:
        """RewriteResult를 딕셔너리로 변환"""
        return {
            "original_query": rewrite_result.original_query,
            "rewritten_queries": rewrite_result.rewritten_queries,
            "confidence": rewrite_result.confidence,
            "improvement_type": rewrite_result.improvement_type,
            "clarification_questions": rewrite_result.clarification_questions,
            "needs_user_input": rewrite_result.needs_user_input
        }

# 사용 예시
if __name__ == "__main__":
    rewriter = RewriterAgent()
    
    # 테스트 케이스들
    test_cases = [
        {
            "query": "삼성전자?",
            "context": {"category": "기업", "entities": {"companies": ["삼성전자"]}}
        },
        {
            "query": "반도체",
            "context": {"category": "기술", "entities": {"keywords": ["반도체"]}}
        },
        {
            "query": "주가가 어떤가요?",
            "context": {"category": "경제", "entities": {"keywords": ["주가"]}}
        },
        {
            "query": "최근 뉴스",
            "context": {"category": "일반"}
        },
        {
            "query": "실적",
            "context": {"category": "기업", "entities": {"keywords": ["실적"]}}
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*70}")
        print(f"테스트 {i}: {test_case['query']}")
        print('='*70)
        
        result = rewriter.rewrite_query(
            test_case["query"], 
            test_case.get("context")
        )
        
        result_dict = rewriter.to_dict(result)
        print(json.dumps(result_dict, ensure_ascii=False, indent=2))
    
    print(f"\n{'='*70}")
    print("RewriterAgent 테스트 완료!")
    print('='*70) 
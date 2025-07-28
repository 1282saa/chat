"""
통합 분석 에이전트 (AnalyzerAgent)
- 질문 명확성 평가 + 날짜 감지 통합
- 카테고리 분류 및 엔티티 추출
- 검색 전략 결정
- 슬림화된 단일 에이전트로 효율성 극대화
"""
import json
import re
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import boto3
from dataclasses import dataclass
import pytz

logger = logging.getLogger()
logger.setLevel(logging.INFO)

@dataclass
class AnalysisResult:
    """분석 결과 데이터 클래스"""
    clarity_score: float
    category: str
    entities: Dict
    temporal_info: Dict
    search_strategy: str
    confidence: float
    needs_clarification: bool
    recommended_actions: List[str]

class AnalyzerAgent:
    """
    질문 분석과 날짜 처리를 통합한 슬림화된 에이전트
    (기존 Query Analyzer + Time Calculator 통합)
    """
    
    def __init__(self):
        # 한국 시간대
        self.kst = pytz.timezone('Asia/Seoul')
        self.current_time = datetime.now(self.kst)
        
        # Bedrock 클라이언트
        self.bedrock_client = boto3.client("bedrock-runtime", region_name="ap-northeast-2")
        
        # 임계값 설정
        self.thresholds = {
            "clarity_minimum": 0.8,      # 재질문 필요 기준
            "freshness_high": 0.7,       # 외부 검색 필요 기준
            "confidence_minimum": 0.75   # 전체 신뢰도 기준
        }
        
        # 뉴스 카테고리 키워드
        self.category_keywords = {
            "경제": ["경제", "금융", "증시", "주가", "실적", "매출", "수익", "투자", "펀드", "은행"],
            "기업": ["기업", "회사", "CEO", "대표", "사업", "경영", "인수", "합병", "상장", "IPO"],
            "정치": ["정부", "정책", "법안", "정치", "국회", "대통령", "장관", "선거", "여당", "야당"],
            "기술": ["기술", "IT", "혁신", "개발", "디지털", "AI", "인공지능", "소프트웨어", "하드웨어"],
            "사회": ["사회", "교육", "의료", "복지", "문화", "스포츠", "연예", "사건", "사고"],
            "국제": ["해외", "미국", "중국", "일본", "유럽", "무역", "외교", "국제", "글로벌"]
        }
        
        # 시간 표현 패턴 (간소화된 버전)
        self.time_patterns = {
            "relative": {
                r'오늘|현재|지금': 0,
                r'어제': -1,
                r'최근|요즘': -7,
                r'작년|지난해': -365,
                r'(\d+)년\s*전': lambda m: -int(m.group(1)) * 365,
                r'(\d+)개?월\s*전': lambda m: -int(m.group(1)) * 30,
                r'(\d+)일\s*전': lambda m: -int(m.group(1))
            },
            "absolute": [
                r'(\d{4})년',
                r'(\d{1,2})월',
                r'상반기|하반기|1분기|2분기|3분기|4분기'
            ],
            "freshness": [
                r'최신|실시간|속보|긴급|라이브'
            ]
        }
        
        # 주요 기업명 패턴
        self.company_patterns = [
            r'삼성[전자|SDI|바이오로직스|화재|물산]*',
            r'LG[전자|화학|에너지솔루션|디스플레이]*',
            r'현대[자동차|모터|중공업|건설]*',
            r'SK[하이닉스|텔레콤|이노베이션|바이오팜]*',
            r'포스코|POSCO',
            r'네이버|NAVER',
            r'카카오|Kakao',
            r'배달의민족|쿠팡|마켓컬리'
        ]
    
    def analyze_query(self, query: str, context: Dict = None, date_context: Dict = None) -> AnalysisResult:
        """
        통합 질문 분석 메인 함수
        """
        try:
            logger.info(f"질문 분석 시작: {query}")
            
            # 날짜 컨텍스트 활용 (사용자 제안 구현)
            if date_context:
                logger.info(f"📅 날짜 컨텍스트 활용: {date_context['현재_날짜_문자열']}")
                # 현재 시간을 date_context에서 가져와서 사용
                self.current_time = date_context['현재_시간']
            
            # 1. 기본 분석
            basic_metrics = self._calculate_basic_metrics(query)
            
            # 2. 카테고리 분류
            category = self._classify_category(query)
            
            # 3. 엔티티 추출
            entities = self._extract_entities(query)
            
            # 4. 시간 정보 분석 (날짜 컨텍스트 활용)
            temporal_info = self._analyze_temporal_expressions(query, date_context)
            
            # 5. 명확성 점수 계산
            clarity_score = self._calculate_clarity_score(query, basic_metrics, entities)
            
            # 6. 검색 전략 결정
            search_strategy = self._determine_search_strategy(temporal_info, category, clarity_score)
            
            # 7. 추천 액션 생성
            recommended_actions = self._generate_recommendations(clarity_score, temporal_info, category)
            
            # 8. 전체 신뢰도 계산
            confidence = self._calculate_overall_confidence(clarity_score, entities, temporal_info)
            
            # 9. 재질문 필요성 판단
            needs_clarification = clarity_score < self.thresholds["clarity_minimum"]
            
            result = AnalysisResult(
                clarity_score=clarity_score,
                category=category,
                entities=entities,
                temporal_info=temporal_info,
                search_strategy=search_strategy,
                confidence=confidence,
                needs_clarification=needs_clarification,
                recommended_actions=recommended_actions
            )
            
            logger.info(f"분석 완료 - 카테고리: {category}, 전략: {search_strategy}, 신뢰도: {confidence:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"질문 분석 중 오류: {str(e)}")
            return self._get_fallback_result(query)
    
    def _calculate_basic_metrics(self, query: str) -> Dict:
        """기본 메트릭 계산"""
        return {
            "length": len(query),
            "word_count": len(query.split()),
            "has_question_mark": "?" in query,
            "has_korean": bool(re.search(r'[가-힣]', query)),
            "has_numbers": bool(re.search(r'\d', query)),
            "has_english": bool(re.search(r'[a-zA-Z]', query))
        }
    
    def _classify_category(self, query: str) -> str:
        """뉴스 카테고리 분류"""
        category_scores = {}
        
        for category, keywords in self.category_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query)
            if score > 0:
                category_scores[category] = score
        
        if category_scores:
            return max(category_scores, key=category_scores.get)
        
        # 기본 분류 로직
        if any(word in query for word in ["주가", "투자", "실적"]):
            return "경제"
        elif any(word in query for word in ["회사", "기업", "CEO"]):
            return "기업"
        else:
            return "일반"
    
    def _extract_entities(self, query: str) -> Dict:
        """주요 엔티티 추출"""
        entities = {
            "companies": [],
            "persons": [],
            "numbers": [],
            "keywords": []
        }
        
        # 기업명 추출
        for pattern in self.company_patterns:
            matches = re.findall(pattern, query, re.IGNORECASE)
            entities["companies"].extend(matches)
        
        # 숫자 추출
        numbers = re.findall(r'\d+(?:\.\d+)?', query)
        entities["numbers"] = [float(n) if '.' in n else int(n) for n in numbers]
        
        # 핵심 키워드 추출 (간단한 버전)
        important_words = ["주가", "실적", "매출", "이익", "전망", "계획", "발표", "출시"]
        entities["keywords"] = [word for word in important_words if word in query]
        
        return entities
    
    def _analyze_temporal_expressions(self, query: str, date_context: Dict = None) -> Dict:
        """시간 표현 분석 - 핵심 기능! (날짜 컨텍스트 활용)"""
        temporal_info = {
            "has_time_expression": False,
            "detected_expressions": [],
            "time_type": "none",
            "calculated_date_range": None,
            "freshness_priority": 0.0,
            "search_mode": "latest_first"  # 기본값
        }
        
        try:
            # 날짜 컨텍스트가 있으면 활용 (사용자 제안 구현)
            if date_context:
                logger.info(f"📅 시간 분석에 날짜 컨텍스트 활용: {date_context['현재_년도']}년 기준")
                
                # DateContextManager의 계산 기능 활용
                from utils.date_context_manager import get_date_context_manager
                date_manager = get_date_context_manager()
                
                # 날짜 관련 질문인지 확인
                if date_manager.is_date_related_query(query):
                    temporal_info["has_time_expression"] = True
                    logger.info(f"🕐 날짜 관련 질문 감지: {query}")
            
            # 1. 상대적 시간 표현 감지
            relative_detected = []
            for pattern, offset in self.time_patterns["relative"].items():
                matches = re.finditer(pattern, query, re.IGNORECASE)
                for match in matches:
                    if callable(offset):
                        days_offset = offset(match)
                    else:
                        days_offset = offset
                    
                    # 날짜 컨텍스트를 활용한 정확한 계산
                    if date_context and date_manager:
                        calculated_date = date_manager.calculate_relative_date(match.group())
                        logger.info(f"✅ '{match.group()}' → {calculated_date['year']}년 (정확한 계산)")
                        
                        relative_detected.append({
                            "expression": match.group(),
                            "days_offset": days_offset,
                            "calculated_year": calculated_date['year'],
                            "calculated_date": calculated_date['date_string'],
                            "type": "relative"
                        })
                    else:
                        relative_detected.append({
                            "expression": match.group(),
                            "days_offset": days_offset,
                            "type": "relative"
                        })
            
            # 2. 절대적 시간 표현 감지
            absolute_detected = []
            for pattern in self.time_patterns["absolute"]:
                matches = re.finditer(pattern, query, re.IGNORECASE)
                for match in matches:
                    absolute_detected.append({
                        "expression": match.group(),
                        "type": "absolute"
                    })
            
            # 3. 신선도 키워드 감지
            freshness_score = 0.0
            for pattern in self.time_patterns["freshness"]:
                if re.search(pattern, query, re.IGNORECASE):
                    freshness_score += 0.3
            
            temporal_info["freshness_priority"] = min(freshness_score, 1.0)
            
            # 4. 감지된 표현들 종합
            all_detected = relative_detected + absolute_detected
            
            if all_detected:
                temporal_info["has_time_expression"] = True
                temporal_info["detected_expressions"] = all_detected
                
                # 가장 구체적인 시간 표현 선택
                if relative_detected:
                    primary_expression = relative_detected[0]
                    temporal_info["time_type"] = "relative"
                    temporal_info["calculated_date_range"] = self._calculate_date_range(primary_expression)
                    temporal_info["search_mode"] = "date_filtered"
                elif absolute_detected:
                    temporal_info["time_type"] = "absolute"
                    temporal_info["search_mode"] = "date_filtered"
            
            # 5. 시간 표현이 없으면 최신순 우선
            if not temporal_info["has_time_expression"]:
                temporal_info["calculated_date_range"] = {
                    "start_date": (self.current_time - timedelta(days=30)).isoformat(),
                    "end_date": self.current_time.isoformat(),
                    "priority": "latest_first",
                    "reason": "no_date_expression_default_to_recent"
                }
                temporal_info["search_mode"] = "latest_first"
            
            return temporal_info
            
        except Exception as e:
            logger.error(f"시간 분석 오류: {str(e)}")
            return {
                "has_time_expression": False,
                "search_mode": "latest_first",
                "calculated_date_range": {
                    "start_date": (self.current_time - timedelta(days=7)).isoformat(),
                    "end_date": self.current_time.isoformat(),
                    "priority": "latest_first",
                    "reason": "fallback_recent"
                }
            }
    
    def _calculate_date_range(self, time_expression: Dict) -> Dict:
        """시간 표현을 실제 날짜 범위로 변환"""
        try:
            days_offset = time_expression["days_offset"]
            target_date = self.current_time + timedelta(days=days_offset)
            
            if days_offset == 0:  # 오늘
                return {
                    "start_date": target_date.replace(hour=0, minute=0, second=0).isoformat(),
                    "end_date": target_date.replace(hour=23, minute=59, second=59).isoformat(),
                    "priority": "date_specific",
                    "reason": "today"
                }
            elif days_offset == -1:  # 어제
                return {
                    "start_date": target_date.replace(hour=0, minute=0, second=0).isoformat(),
                    "end_date": target_date.replace(hour=23, minute=59, second=59).isoformat(),
                    "priority": "date_specific",
                    "reason": "yesterday"
                }
            elif days_offset <= -30:  # 한 달 이상 전
                return {
                    "start_date": (target_date - timedelta(days=30)).isoformat(),
                    "end_date": (target_date + timedelta(days=30)).isoformat(),
                    "priority": "date_range",
                    "reason": f"around_{abs(days_offset)}_days_ago"
                }
            else:  # 최근 (7일 전 등)
                return {
                    "start_date": (target_date - timedelta(days=3)).isoformat(),
                    "end_date": (target_date + timedelta(days=3)).isoformat(),
                    "priority": "recent_range",
                    "reason": "recent_period"
                }
                
        except Exception as e:
            logger.error(f"날짜 범위 계산 오류: {str(e)}")
            return {
                "start_date": (self.current_time - timedelta(days=7)).isoformat(),
                "end_date": self.current_time.isoformat(),
                "priority": "latest_first",
                "reason": "calculation_error_fallback"
            }
    
    def _calculate_clarity_score(self, query: str, basic_metrics: Dict, entities: Dict) -> float:
        """질문 명확성 점수 계산"""
        score = 0.5  # 기본 점수
        
        # 길이 평가
        if basic_metrics["length"] > 10:
            score += 0.1
        if basic_metrics["word_count"] >= 3:
            score += 0.1
        
        # 질문 형태 평가
        if basic_metrics["has_question_mark"]:
            score += 0.15
        
        # 구체성 평가
        if entities["companies"]:
            score += 0.15  # 구체적인 기업명 있음
        if entities["keywords"]:
            score += 0.1   # 관련 키워드 있음
        
        # 부정 요소
        if basic_metrics["length"] < 5:
            score -= 0.3
        if not basic_metrics["has_korean"] and not basic_metrics["has_english"]:
            score -= 0.2
        
        # 애매한 표현 감지
        vague_patterns = [r'^[가-힣]{1,3}\?*$', r'^[a-zA-Z]{1,5}\?*$']
        if any(re.match(pattern, query) for pattern in vague_patterns):
            score -= 0.4
        
        return max(0.0, min(1.0, score))
    
    def _determine_search_strategy(self, temporal_info: Dict, category: str, clarity_score: float) -> str:
        """검색 전략 결정"""
        
        # 명확성이 낮으면 재질문 우선
        if clarity_score < self.thresholds["clarity_minimum"]:
            return "clarification_first"
        
        # 시간 표현이 있으면 날짜 기반 검색
        if temporal_info["has_time_expression"]:
            return "date_filtered_search"
        
        # 신선도가 높게 요구되면 외부 검색 포함
        if temporal_info["freshness_priority"] > self.thresholds["freshness_high"]:
            return "fresh_content_priority"
        
        # 복잡한 카테고리는 다단계 검색
        if category in ["경제", "정치"]:
            return "multi_source_search"
        
        # 기본값: 최신순 검색
        return "latest_first_search"
    
    def _generate_recommendations(self, clarity_score: float, temporal_info: Dict, category: str) -> List[str]:
        """추천 액션 생성"""
        actions = []
        
        # 필수: 내부 검색
        actions.append("internal_search")
        
        # 조건부: 재질문
        if clarity_score < self.thresholds["clarity_minimum"]:
            actions.append("query_clarification")
        
        # 조건부: 외부 검색
        if (temporal_info["freshness_priority"] > self.thresholds["freshness_high"] or
            not temporal_info["has_time_expression"]):
            actions.append("external_search")
        
        # 조건부: 날짜 필터링
        if temporal_info["has_time_expression"]:
            actions.append("date_filtering")
        
        # 필수: 답변 생성
        actions.append("answer_synthesis")
        
        return actions
    
    def _calculate_overall_confidence(self, clarity_score: float, entities: Dict, temporal_info: Dict) -> float:
        """전체 신뢰도 계산"""
        confidence = clarity_score * 0.4  # 명확성 40%
        
        # 엔티티 존재로 신뢰도 증가
        if entities["companies"]:
            confidence += 0.2
        if entities["keywords"]:
            confidence += 0.1
        
        # 시간 정보로 신뢰도 증가
        if temporal_info["has_time_expression"]:
            confidence += 0.15
        else:
            confidence += 0.1  # 최신순 검색도 유효
        
        # 신선도 요구사항으로 조정
        freshness_bonus = temporal_info["freshness_priority"] * 0.15
        confidence += freshness_bonus
        
        return min(confidence, 1.0)
    
    def _get_fallback_result(self, query: str) -> AnalysisResult:
        """Fallback 분석 결과"""
        return AnalysisResult(
            clarity_score=0.6,
            category="일반",
            entities={"companies": [], "persons": [], "numbers": [], "keywords": []},
            temporal_info={
                "has_time_expression": False,
                "search_mode": "latest_first",
                "calculated_date_range": {
                    "start_date": (self.current_time - timedelta(days=7)).isoformat(),
                    "end_date": self.current_time.isoformat(),
                    "priority": "latest_first",
                    "reason": "fallback"
                }
            },
            search_strategy="latest_first_search",
            confidence=0.5,
            needs_clarification=False,
            recommended_actions=["internal_search", "answer_synthesis"]
        )
    
    def generate_clarification_questions(self, query: str, analysis_result: AnalysisResult) -> List[str]:
        """재질문 생성"""
        questions = []
        
        # 카테고리별 구체화 질문
        if analysis_result.category == "경제":
            questions.extend([
                "구체적으로 어떤 경제 지표에 대해 알고 싶으신가요?",
                "특정 시기의 경제 상황을 원하시나요?",
                "전반적인 경제 동향을 원하시나요?"
            ])
        elif analysis_result.category == "기업":
            questions.extend([
                "특정 기업의 어떤 측면이 궁금하신가요? (실적, 주가, 사업 계획 등)",
                "최근 소식을 원하시나요, 아니면 특정 시점의 정보를 원하시나요?"
            ])
        
        # 시간 관련 구체화
        if not analysis_result.temporal_info["has_time_expression"]:
            questions.append("언제 시점의 정보를 원하시나요? (최근, 특정 날짜, 기간 등)")
        
        # 엔티티 관련 구체화
        if not analysis_result.entities["companies"] and analysis_result.category in ["경제", "기업"]:
            questions.append("특정 회사나 기업에 대한 정보를 원하시나요?")
        
        return questions[:3]  # 최대 3개
    
    def to_dict(self, analysis_result: AnalysisResult) -> Dict:
        """AnalysisResult를 딕셔너리로 변환"""
        return {
            "clarity_score": analysis_result.clarity_score,
            "category": analysis_result.category,
            "entities": analysis_result.entities,
            "temporal_info": analysis_result.temporal_info,
            "search_strategy": analysis_result.search_strategy,
            "confidence": analysis_result.confidence,
            "needs_clarification": analysis_result.needs_clarification,
            "recommended_actions": analysis_result.recommended_actions
        }

# 사용 예시
if __name__ == "__main__":
    analyzer = AnalyzerAgent()
    
    # 테스트 케이스들
    test_queries = [
        "삼양식품 주가는 어떤가요?",           # 명확, 날짜 없음 → 최신순
        "1년 전 삼성전자는 어땠나요?",         # 명확, 날짜 있음 → 날짜 필터링
        "어제 주요 뉴스는?",                  # 보통, 날짜 있음 → 날짜 특정
        "반도체?",                           # 애매 → 재질문 필요
        "최신 경제 동향 분석해줘",            # 신선도 높음 → 외부 검색
        "작년 상반기 실적"                    # 절대 날짜 → 날짜 필터링
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"테스트 {i}: {query}")
        print('='*60)
        
        result = analyzer.analyze_query(query)
        result_dict = analyzer.to_dict(result)
        
        print(json.dumps(result_dict, ensure_ascii=False, indent=2))
        
        # 재질문이 필요한 경우
        if result.needs_clarification:
            questions = analyzer.generate_clarification_questions(query, result)
            print(f"\n재질문 후보:")
            for j, q in enumerate(questions, 1):
                print(f"  {j}. {q}")
    
    print(f"\n{'='*60}")
    print("AnalyzerAgent 테스트 완료!")
    print('='*60) 
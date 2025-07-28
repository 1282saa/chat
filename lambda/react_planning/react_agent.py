"""
ReAct Planning Agent
- Chain-of-Thought(CoT) 사고 과정 구현
- 질문 분석 및 실행 계획 수립
- 조건부 에이전트 호출 결정
"""
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import re
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class ReactPlanningAgent:
    """
    ReAct 기법을 사용한 지능형 Planning Agent
    Thought → Action → Observation → Answer 구조
    """
    
    def __init__(self):
        self.current_date = datetime.now()
        self.bedrock_client = boto3.client("bedrock-runtime", region_name=os.environ.get("REGION", "ap-northeast-2"))
        
        # APAC 지역 Claude 모델 설정 (서울 리전 최적화)
        self.apac_models = {
            "fast": "apac.anthropic.claude-3-haiku-20240307-v1:0",          # 1.89초 - 빠른 계획
            "balanced": "apac.anthropic.claude-3-sonnet-20240229-v1:0",     # 3.22초 - 균형
            "advanced": "apac.anthropic.claude-3-7-sonnet-20250219-v1:0",   # 4.17초 - 2025년 최신
            "high_performance": "apac.anthropic.claude-3-5-sonnet-20240620-v1:0",  # 3.92초 - 고성능
            "premium": "apac.anthropic.claude-sonnet-4-20250514-v1:0",      # 4.48초 - 최고급
            "latest": "apac.anthropic.claude-3-5-sonnet-20241022-v2:0"      # 5.78초 - 최신 v2
        }
        
        # 기본 모델 설정 (ReAct 계획에는 빠른 응답이 중요)
        model_tier = os.environ.get("REACT_MODEL_TIER", "fast")
        self.default_model = self.apac_models.get(model_tier, self.apac_models["fast"])
        
        logger.info(f"🧠 ReactPlanningAgent 초기화 - 사용 모델: {self.default_model}")
        
        # 임계값 설정
        self.thresholds = {
            "query_clarity": 0.8,        # 재질문 필요 여부
            "internal_coverage": 0.7,    # 외부 검색 필요 여부  
            "answer_quality": 0.85,      # 재생성 필요 여부
            "freshness_requirement": 0.6, # 실시간 정보 필요 여부
            "date_sensitivity": 0.9      # 날짜 기반 검색 필요 여부
        }
        
        # 날짜 표현 패턴
        self.date_patterns = {
            "relative": [
                r'오늘', r'어제', r'그제', r'모레', r'내일',
                r'이번\s*주', r'지난\s*주', r'다음\s*주',
                r'이번\s*달', r'지난\s*달', r'다음\s*달',
                r'올해', r'작년', r'내년',
                r'최근', r'최신', r'요즘'
            ],
            "specific_period": [
                r'\d+년\s*전', r'\d+달\s*전', r'\d+개월\s*전', 
                r'\d+주\s*전', r'\d+일\s*전',
                r'\d{4}년', r'\d{1,2}월', r'\d{1,2}일'
            ],
            "season": [
                r'봄', r'여름', r'가을', r'겨울',
                r'상반기', r'하반기', r'분기'
            ]
        }
    
    def plan_execution(self, query: str, context: Dict = None) -> Dict:
        """
        메인 Planning 함수: ReAct 기법 적용
        """
        try:
            # Step 1: Thought (사고)
            thinking_result = self._analyze_query_cot(query, context)
            
            # Step 2: Action (행동 계획)
            action_plan = self._determine_actions(thinking_result)
            
            # Step 3: Observation (관찰 및 검증)
            observations = self._validate_plan(action_plan)
            
            # Step 4: Final Answer (최종 계획)
            final_plan = self._synthesize_plan(thinking_result, action_plan, observations)
            
            return final_plan
            
        except Exception as e:
            logger.error(f"Planning 실행 중 오류: {str(e)}")
            return self._get_fallback_plan(query)
    
    def _analyze_query_cot(self, query: str, context: Dict = None) -> Dict:
        """
        Chain-of-Thought 기법으로 질문 분석
        """
        
        # 1. 기본 정보 추출
        basic_analysis = {
            "original_query": query,
            "query_length": len(query),
            "question_type": self._classify_question_type(query),
            "entities": self._extract_entities(query),
            "current_time": self.current_date.isoformat()
        }
        
        # 2. 날짜 표현 분석 (핵심 추가 기능)
        date_analysis = self._analyze_date_expressions(query)
        
        # 3. 질문 명확성 평가
        clarity_score = self._evaluate_query_clarity(query)
        
        # 4. 내용 복잡도 분석
        complexity_analysis = self._analyze_complexity(query)
        
        # 5. CoT 사고 과정 프롬프트
        cot_prompt = f"""
당신은 뉴스 질문 분석 전문가입니다. 다음 질문을 단계별로 분석해주세요.

질문: "{query}"
현재 시간: {self.current_date.strftime('%Y-%m-%d %H:%M')} (한국시간)

### 사고 과정:

**1단계 - 질문 이해**:
- 사용자가 진짜 알고 싶어하는 것은 무엇인가?
- 질문의 핵심 의도는 무엇인가?
- 어떤 종류의 정보를 원하는가?

**2단계 - 시간성 분석**:
- 특정 시점에 대한 질문인가?
- 실시간 정보가 필요한가?
- 과거 데이터로 충분한가?

**3단계 - 정보 범위 판단**:
- 내부 뉴스 DB에서 찾을 수 있는 내용인가?
- 외부 검색이 필요한 내용인가?
- 복합적인 분석이 필요한가?

**4단계 - 응답 전략**:
- 어떤 순서로 정보를 수집해야 하는가?
- 어떤 에이전트들이 필요한가?
- 예상되는 어려움은 무엇인가?

JSON 형식으로 분석 결과를 출력하세요:
{{
    "understanding": "질문 의도 분석",
    "time_sensitivity": "시간성 분석",
    "information_scope": "정보 범위 판단", 
    "response_strategy": "응답 전략",
    "confidence": 0.0-1.0,
    "complexity_level": "simple|moderate|complex"
}}
"""
        
        try:
            # Bedrock으로 CoT 분석 실행
            cot_result = self._call_bedrock_analysis(cot_prompt)
            
            return {
                "basic_analysis": basic_analysis,
                "date_analysis": date_analysis,
                "clarity_score": clarity_score,
                "complexity_analysis": complexity_analysis,
                "cot_thinking": cot_result,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"CoT 분석 중 오류: {str(e)}")
            return self._get_fallback_analysis(query, basic_analysis, date_analysis)
    
    def _analyze_date_expressions(self, query: str) -> Dict:
        """
        날짜 표현 분석 - 핵심 기능!
        """
        detected_expressions = []
        date_type = "none"
        calculated_range = None
        
        # 1. 상대적 날짜 표현 감지
        for pattern in self.date_patterns["relative"]:
            if re.search(pattern, query, re.IGNORECASE):
                detected_expressions.append(pattern)
                date_type = "relative"
        
        # 2. 구체적 기간 표현 감지  
        for pattern in self.date_patterns["specific_period"]:
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                detected_expressions.extend(matches)
                date_type = "specific"
        
        # 3. 계절/분기 표현 감지
        for pattern in self.date_patterns["season"]:
            if re.search(pattern, query, re.IGNORECASE):
                detected_expressions.append(pattern)
                date_type = "seasonal"
        
        # 4. 날짜 범위 계산
        if detected_expressions:
            calculated_range = self._calculate_date_range(detected_expressions, query)
        else:
            # 날짜 표현이 없으면 최신순 (오늘부터 30일 전)
            calculated_range = {
                "start_date": (self.current_date - timedelta(days=30)).isoformat(),
                "end_date": self.current_date.isoformat(),
                "priority": "latest_first",
                "reason": "no_date_expression_default_to_recent"
            }
        
        return {
            "has_date_expression": len(detected_expressions) > 0,
            "detected_expressions": detected_expressions,
            "date_type": date_type,
            "calculated_range": calculated_range,
            "requires_date_filtering": len(detected_expressions) > 0,
            "freshness_priority": 0.9 if date_type == "none" else 0.5
        }
    
    def _calculate_date_range(self, expressions: List[str], query: str) -> Dict:
        """
        날짜 표현을 실제 날짜 범위로 변환
        """
        current = self.current_date
        
        for expr in expressions:
            # "N년 전" 패턴
            year_match = re.search(r'(\d+)년\s*전', expr)
            if year_match:
                years_ago = int(year_match.group(1))
                target_date = current - timedelta(days=365 * years_ago)
                return {
                    "start_date": (target_date - timedelta(days=30)).isoformat(),
                    "end_date": (target_date + timedelta(days=30)).isoformat(),
                    "priority": "date_specific",
                    "reason": f"{years_ago}년 전 기준"
                }
            
            # "N개월 전" 패턴
            month_match = re.search(r'(\d+)(달|개월)\s*전', expr)
            if month_match:
                months_ago = int(month_match.group(1))
                target_date = current - timedelta(days=30 * months_ago)
                return {
                    "start_date": (target_date - timedelta(days=15)).isoformat(),
                    "end_date": (target_date + timedelta(days=15)).isoformat(),
                    "priority": "date_specific",
                    "reason": f"{months_ago}개월 전 기준"
                }
            
            # "어제", "오늘" 등
            if "어제" in expr:
                yesterday = current - timedelta(days=1)
                return {
                    "start_date": yesterday.replace(hour=0, minute=0, second=0).isoformat(),
                    "end_date": yesterday.replace(hour=23, minute=59, second=59).isoformat(),
                    "priority": "date_specific",
                    "reason": "어제 날짜 기준"
                }
            
            if "오늘" in expr or "최신" in expr or "최근" in expr:
                return {
                    "start_date": current.replace(hour=0, minute=0, second=0).isoformat(),
                    "end_date": current.isoformat(),
                    "priority": "latest_first",
                    "reason": "오늘/최신 기준"
                }
        
        # 기본값: 최근 7일
        return {
            "start_date": (current - timedelta(days=7)).isoformat(),
            "end_date": current.isoformat(),
            "priority": "latest_first",
            "reason": "기본 최근 7일"
        }
    
    def _determine_actions(self, thinking_result: Dict) -> Dict:
        """
        분석 결과를 바탕으로 실행할 액션들 결정
        """
        actions = []
        
        # 1. 질문 명확성 검토
        if thinking_result["clarity_score"] < self.thresholds["query_clarity"]:
            actions.append({
                "type": "query_rewrite",
                "priority": 1,
                "reason": "질문이 애매모호함",
                "agent": "RewriterAgent"
            })
        
        # 2. 날짜 기반 검색 필요성
        if thinking_result["date_analysis"]["requires_date_filtering"]:
            actions.append({
                "type": "date_filtered_search",
                "priority": 2,
                "reason": "날짜 기반 검색 필요",
                "agent": "SearchAgent",
                "date_range": thinking_result["date_analysis"]["calculated_range"]
            })
        else:
            actions.append({
                "type": "latest_first_search", 
                "priority": 2,
                "reason": "최신순 검색 적용",
                "agent": "SearchAgent",
                "date_range": thinking_result["date_analysis"]["calculated_range"]
            })
        
        # 3. 내부 검색 우선
        actions.append({
            "type": "internal_search",
            "priority": 3,
            "reason": "내부 Knowledge Base 검색",
            "agent": "SearchAgent"
        })
        
        # 4. 외부 검색 조건부 실행
        if (thinking_result.get("complexity_analysis", {}).get("requires_external", False) or 
            thinking_result["date_analysis"]["freshness_priority"] > 0.8):
            actions.append({
                "type": "external_search",
                "priority": 4,
                "reason": "외부 검색 필요 (신선도/복잡도)",
                "agent": "SearchAgent", 
                "condition": "if_internal_insufficient"
            })
        
        # 5. 답변 생성
        actions.append({
            "type": "answer_synthesis",
            "priority": 5,
            "reason": "최종 답변 생성",
            "agent": "SynthesizerAgent"
        })
        
        # 6. 품질 검증
        actions.append({
            "type": "quality_check",
            "priority": 6,
            "reason": "답변 품질 검증",
            "agent": "QualityGateAgent"
        })
        
        return {
            "actions": sorted(actions, key=lambda x: x["priority"]),
            "total_actions": len(actions),
            "estimated_time": self._estimate_execution_time(actions),
            "fallback_plan": self._create_fallback_actions()
        }
    
    def _validate_plan(self, action_plan: Dict) -> Dict:
        """
        실행 계획 검증 및 관찰
        """
        observations = {
            "plan_feasibility": 0.9,
            "resource_requirements": {},
            "potential_issues": [],
            "optimization_suggestions": []
        }
        
        # 액션 수 검증
        if action_plan["total_actions"] > 8:
            observations["potential_issues"].append("액션 수가 많아 지연 가능성")
            observations["optimization_suggestions"].append("액션 병렬 처리 권장")
        
        # 외부 검색 비용 검증
        external_actions = [a for a in action_plan["actions"] if a["type"] == "external_search"]
        if len(external_actions) > 0:
            observations["resource_requirements"]["external_api_calls"] = len(external_actions)
            observations["potential_issues"].append("외부 API 비용 발생")
        
        return observations
    
    def _synthesize_plan(self, thinking: Dict, actions: Dict, observations: Dict) -> Dict:
        """
        최종 실행 계획 합성
        """
        return {
            "plan_id": f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "original_query": thinking["basic_analysis"]["original_query"],
            "analysis_summary": {
                "question_type": thinking["basic_analysis"]["question_type"],
                "has_date_expression": thinking["date_analysis"]["has_date_expression"],
                "complexity_level": thinking.get("complexity_analysis", {}).get("level", "moderate"),
                "clarity_score": thinking["clarity_score"]
            },
            "execution_plan": {
                "actions": actions["actions"],
                "estimated_time": actions["estimated_time"],
                "fallback_available": True
            },
            "date_strategy": thinking["date_analysis"]["calculated_range"],
            "validation_result": observations,
            "recommendations": {
                "use_cache": thinking["date_analysis"]["date_type"] != "none",
                "parallel_execution": len(actions["actions"]) > 4,
                "monitoring_required": observations["plan_feasibility"] < 0.8
            },
            "created_at": datetime.now().isoformat()
        }
    
    # Helper methods
    def _classify_question_type(self, query: str) -> str:
        """질문 유형 분류"""
        if any(word in query for word in ["어떻게", "방법", "how"]):
            return "how_to"
        elif any(word in query for word in ["왜", "이유", "why"]):
            return "explanation"
        elif any(word in query for word in ["언제", "when", "시간", "날짜"]):
            return "temporal"
        elif any(word in query for word in ["누구", "who", "인물"]):
            return "person"
        elif any(word in query for word in ["어디", "where", "장소"]):
            return "location"
        elif "?" in query or "인가" in query:
            return "question"
        else:
            return "statement"
    
    def _extract_entities(self, query: str) -> Dict:
        """엔티티 추출 (간단한 버전)"""
        entities = {
            "companies": [],
            "persons": [],
            "locations": [],
            "keywords": []
        }
        
        # 기업명 패턴 (간단한 버전)
        company_patterns = [
            r'삼성[전자|화재|바이오]*', r'LG[전자|화학|디스플레이]*',
            r'현대[자동차|모터]*', r'SK[하이닉스|텔레콤]*',
            r'네이버', r'카카오', r'배달의민족', r'쿠팡'
        ]
        
        for pattern in company_patterns:
            matches = re.findall(pattern, query)
            entities["companies"].extend(matches)
        
        return entities
    
    def _evaluate_query_clarity(self, query: str) -> float:
        """질문 명확성 점수 계산"""
        score = 0.5  # 기본 점수
        
        # 긍정 요소
        if len(query) > 10: score += 0.1
        if "?" in query: score += 0.1
        if any(word in query for word in ["무엇", "어떻게", "왜", "언제", "어디"]): score += 0.2
        if len(query.split()) >= 3: score += 0.1
        
        # 부정 요소  
        if len(query) < 5: score -= 0.3
        if query.count("?") > 2: score -= 0.1
        if not any(char.isalpha() for char in query): score -= 0.2
        
        return max(0.0, min(1.0, score))
    
    def _analyze_complexity(self, query: str) -> Dict:
        """질문 복잡도 분석"""
        complexity_score = 0.3  # 기본값
        
        # 복잡도 증가 요소
        if len(query.split()) > 10: complexity_score += 0.2
        if "비교" in query or "차이" in query: complexity_score += 0.2
        if "분석" in query or "평가" in query: complexity_score += 0.3
        if "전망" in query or "예측" in query: complexity_score += 0.2
        
        level = "simple"
        if complexity_score > 0.7: level = "complex"
        elif complexity_score > 0.5: level = "moderate"
        
        return {
            "score": complexity_score,
            "level": level,
            "requires_external": complexity_score > 0.6,
            "estimated_tokens": len(query) * 1.5
        }
    
    def _call_bedrock_analysis(self, prompt: str) -> Dict:
        """Bedrock을 호출하여 CoT 분석 실행"""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.default_model,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # JSON 파싱 시도
            try:
                return json.loads(content)
            except:
                return {"raw_response": content, "parsed": False}
                
        except Exception as e:
            logger.error(f"Bedrock 호출 오류: {str(e)}")
            return {"error": str(e), "fallback": True}
    
    def _get_fallback_analysis(self, query: str, basic: Dict, date: Dict) -> Dict:
        """Fallback 분석 결과"""
        return {
            "basic_analysis": basic,
            "date_analysis": date,
            "clarity_score": 0.6,
            "complexity_analysis": {"level": "moderate", "score": 0.5},
            "cot_thinking": {"fallback": True},
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def _get_fallback_plan(self, query: str) -> Dict:
        """Fallback 실행 계획"""
        return {
            "plan_id": f"fallback_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "original_query": query,
            "execution_plan": {
                "actions": [
                    {"type": "simple_search", "priority": 1, "agent": "SearchAgent"},
                    {"type": "basic_answer", "priority": 2, "agent": "SynthesizerAgent"}
                ]
            },
            "fallback": True,
            "created_at": datetime.now().isoformat()
        }
    
    def _estimate_execution_time(self, actions: List[Dict]) -> int:
        """실행 시간 추정 (초)"""
        time_map = {
            "query_rewrite": 2,
            "internal_search": 3,
            "external_search": 5,
            "date_filtered_search": 4,
            "answer_synthesis": 3,
            "quality_check": 1
        }
        
        total_time = sum(time_map.get(action["type"], 2) for action in actions)
        return min(total_time, 20)  # 최대 20초로 제한
    
    def _create_fallback_actions(self) -> List[Dict]:
        """Fallback 액션 생성"""
        return [
            {"type": "simple_search", "priority": 1, "agent": "SearchAgent"},
            {"type": "basic_answer", "priority": 2, "agent": "SynthesizerAgent"}
        ]

# 사용 예시
if __name__ == "__main__":
    agent = ReactPlanningAgent()
    
    # 테스트 케이스 1: 날짜 표현 없음 (최신순)
    result1 = agent.plan_execution("삼양식품 주가는 어떤가요?")
    print("=== 테스트 1: 날짜 표현 없음 ===")
    print(json.dumps(result1, ensure_ascii=False, indent=2))
    
    # 테스트 케이스 2: 상대적 날짜 표현
    result2 = agent.plan_execution("1년 전 삼양식품은 어땠나요?")
    print("\n=== 테스트 2: 상대적 날짜 ===")
    print(json.dumps(result2, ensure_ascii=False, indent=2)) 
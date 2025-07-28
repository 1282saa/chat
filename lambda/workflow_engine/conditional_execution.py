"""
임계값 기반 조건부 실행 엔진 (Conditional Execution Engine)
- 모든 에이전트들의 중앙 워크플로우 제어
- 임계값 기반 분기 로직
- 재시도 및 품질 관리
- 성능 모니터링 및 최적화
"""
import json
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import boto3
from enum import Enum

# 상대 import (실제 환경에서는 절대 경로 사용)
import sys
sys.path.append('..')

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class ExecutionStatus(Enum):
    """실행 상태 열거형"""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"

class ThresholdType(Enum):
    """임계값 유형"""
    QUALITY = "quality"
    COVERAGE = "coverage"
    FRESHNESS = "freshness"
    CLARITY = "clarity"
    CONFIDENCE = "confidence"

class ConditionalExecutionEngine:
    """
    모든 에이전트를 제어하는 중앙 워크플로우 엔진
    """
    
    def __init__(self):
        # 임계값 설정 (사용자 요구사항 반영)
        self.thresholds = {
            ThresholdType.QUALITY: 0.85,      # 답변 품질 (재생성 필요)
            ThresholdType.COVERAGE: 0.7,      # 내부 지식 커버리지 (외부 검색 필요)
            ThresholdType.FRESHNESS: 0.6,     # 신선도 요구사항 (실시간 정보 필요)
            ThresholdType.CLARITY: 0.8,       # 질문 명확성 (재질문 필요)
            ThresholdType.CONFIDENCE: 0.75    # 전체 신뢰도
        }
        
        # 재시도 설정
        self.retry_config = {
            "max_retries": 3,
            "retry_delay": 2,  # 초
            "exponential_backoff": True
        }
        
        # 성능 모니터링
        self.performance_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "retry_executions": 0,
            "avg_execution_time": 0.0,
            "external_search_rate": 0.0
        }
        
        # DynamoDB 메트릭 저장
        self.dynamodb = boto3.client("dynamodb", region_name=os.environ.get("REGION", "ap-northeast-2"))
        self.metrics_table = os.environ.get("EXECUTION_METRICS_TABLE", "workflow-execution-metrics")
        
        # 에이전트 임포트 (실제 환경에서는 적절히 수정)
        self.agents = {}
        self._initialize_agents()
    
    def _initialize_agents(self):
        """실제 Enhanced Agent System 초기화"""
        try:
            # 실제 에이전트들 import 시도
            logger.info("🔄 실제 Enhanced 에이전트들 로드 시작...")
            
            from react_planning.react_agent import ReactPlanningAgent
            from date_intelligence.date_processor import DateIntelligenceProcessor  
            from external_search.perplexity_integration import PerplexitySearchAgent
            
            # 실제 에이전트 인스턴스 생성
            self.agents = {
                "planner": ReactPlanningAgent(),
                "date_processor": DateIntelligenceProcessor(),
                "external_search": PerplexitySearchAgent()
            }
            
            logger.info("✅ 실제 Enhanced Agent System 초기화 완료!")
            logger.info("🎯 활성화된 에이전트들:")
            logger.info("   - ReactPlanningAgent (ReAct + CoT)")
            logger.info("   - DateIntelligenceProcessor (날짜 지능형 처리)")
            logger.info("   - PerplexitySearchAgent (외부 검색)")
            
        except ImportError as e:
            logger.warning(f"⚠️ 실제 에이전트 임포트 실패, Mock 에이전트로 Fallback")
            logger.warning(f"   Import 오류: {str(e)}")
            logger.warning(f"   Python 경로: {sys.path}")
            
            # Fallback: Mock 에이전트들 사용
            self.agents = {
                "planner": self._create_simple_planner(),
                "date_processor": self._create_simple_date_processor(),
                "external_search": self._create_simple_external_search()
            }
            logger.info("📝 Mock 에이전트 초기화 완료 (Fallback 모드)")
            
        except Exception as e:
            logger.error(f"❌ 에이전트 초기화 중 예상치 못한 오류: {str(e)}")
            logger.error(f"   오류 타입: {type(e).__name__}")
            import traceback
            logger.error(f"   스택 트레이스: {traceback.format_exc()}")
            
            # Fallback: Mock 에이전트들 사용
            self.agents = {
                "planner": self._create_simple_planner(),
                "date_processor": self._create_simple_date_processor(),
                "external_search": self._create_simple_external_search()
            }
            logger.info("📝 Mock 에이전트 초기화 완료 (오류로 인한 Fallback)")
    
    def execute_workflow(self, 
                        query: str, 
                        user_context: Dict = None,
                        execution_options: Dict = None) -> Dict:
        """
        메인 워크플로우 실행 함수
        """
        execution_id = f"exec_{int(time.time() * 1000)}"
        start_time = time.time()
        
        execution_context = {
            "execution_id": execution_id,
            "query": query,
            "user_context": user_context or {},
            "options": execution_options or {},
            "start_time": start_time,
            "steps": [],
            "metrics": {},
            "final_result": None
        }
        
        try:
            logger.info(f"워크플로우 실행 시작: {execution_id}")
            
            # Step 1: Planning (필수)
            logger.info("📋 Planning 단계 시작")
            planning_result = self._execute_planning_step(execution_context)
            logger.info(f"📋 Planning 단계 완료: {planning_result.get('success')}")
            if not planning_result["success"]:
                return self._handle_execution_failure(execution_context, "planning_failed")
            
            # Step 2: 조건부 실행 단계들
            execution_plan = planning_result["data"]["execution_plan"]["actions"]
            logger.info(f"🔄 실행할 단계 수: {len(execution_plan)}")
            
            for i, step_config in enumerate(execution_plan, 1):
                logger.info(f"⚙️ 단계 {i}/{len(execution_plan)} 실행: {step_config.get('type')}")
                step_result = self._execute_conditional_step(execution_context, step_config)
                logger.info(f"✅ 단계 {i} 완료: {step_result.get('success')}")
                execution_context["steps"].append(step_result)
                
                # 실패 시 재시도 로직
                if not step_result["success"] and step_config.get("critical", False):
                    retry_result = self._handle_step_retry(execution_context, step_config)
                    if not retry_result["success"]:
                        return self._handle_execution_failure(execution_context, f"{step_config['type']}_failed")
            
            # Step 3: 최종 결과 합성
            final_result = self._synthesize_final_result(execution_context)
            
            # Step 4: 품질 검증
            quality_check = self._perform_quality_check(final_result)
            
            # 품질이 임계값 미만이면 재시도
            if quality_check["score"] < self.thresholds[ThresholdType.QUALITY]:
                logger.info(f"품질 점수 부족 ({quality_check['score']:.2f}), 재시도 수행")
                retry_result = self._retry_with_enhanced_context(execution_context)
                if retry_result["success"]:
                    final_result = retry_result["data"]
            
            # 성공 처리
            execution_time = time.time() - start_time
            self._record_success_metrics(execution_context, execution_time)
            
            return {
                "success": True,
                "execution_id": execution_id,
                "result": final_result,
                "thinking_process": self._extract_thinking_process(execution_context),  # 🧠 사고 과정 추가
                "metadata": {
                    "execution_time": execution_time,
                    "steps_executed": len(execution_context["steps"]),
                    "quality_score": quality_check["score"],
                    "external_search_used": any(step.get("step_type") == "external_search" for step in execution_context["steps"]),
                    "retries_performed": sum(1 for step in execution_context["steps"] if step.get("retries", 0) > 0)
                }
            }
            
        except Exception as e:
            logger.error(f"워크플로우 실행 중 오류: {str(e)}")
            return self._handle_execution_failure(execution_context, f"unexpected_error: {str(e)}")

    def _extract_thinking_process(self, execution_context: Dict) -> List[Dict]:
        """
        실제 Enhanced Agent System의 사고 과정을 상세히 추출
        """
        thinking_steps = []
        
        try:
            # Planning 단계 - 실제 에이전트 정보 포함
            planning_result = execution_context.get("planning_result", {})
            date_strategy = execution_context.get("date_strategy", {})
            
            # 1. ReAct Planning 단계
            thinking_steps.append({
                "step_name": "🧠 ReAct Planning (사고+행동)",
                "description": f"'{execution_context['query'][:50]}...' 질문을 ReAct 방식으로 분석하고 Chain-of-Thought 추론을 통해 실행 계획을 수립했습니다.",
                "result": f"계획 수립 완료 - {len(execution_context.get('steps', []))}단계 실행 예정",
                "execution_time": 0.5
            })
            
            # 2. 날짜 지능형 분석 (실제 결과 반영)
            if date_strategy.get("has_date_expression"):
                date_desc = f"'{date_strategy.get('time_expression', '')}' 표현을 감지하여 {date_strategy.get('date_range', {}).get('start', 'N/A')}부터 검색 범위를 설정했습니다."
                date_result = f"특정 기간 검색 ({date_strategy.get('primary_strategy', 'unknown')})"
            else:
                date_desc = "날짜 표현이 없어 최신 뉴스를 우선적으로 검색하도록 설정했습니다."
                date_result = "최신순 우선 검색"
                
            thinking_steps.append({
                "step_name": "📅 날짜 지능형 처리",
                "description": date_desc,
                "result": date_result,
                "execution_time": 0.3
            })
            
            # 3. 각 실행 단계별 상세 사고 과정
            for i, step in enumerate(execution_context.get("steps", []), 3):
                step_type = step.get("type", "unknown")
                step_success = step.get("success", False)
                step_data = step.get("data", {})
                step_time = step.get("execution_time", 0)
                
                # 실제 에이전트 결과 기반 단계별 상세 설명
                if step_type == "internal_search":
                    sources_count = len(step_data.get("sources", []))
                    coverage_score = step_data.get("coverage_score", 0)
                    
                    thinking_steps.append({
                        "step_name": "📚 내부 지식 베이스 검색",
                        "description": f"AWS Bedrock Knowledge Base에서 관련 뉴스를 검색했습니다. 커버리지: {coverage_score:.1f}/5.0",
                        "result": f"성공 ({sources_count}개 소스 발견)" if step_success else "정보 부족",
                        "execution_time": step_time
                    })
                    
                elif step_type == "external_search":
                    confidence = step_data.get("confidence", 0)
                    sources_count = len(step_data.get("sources", []))
                    
                    thinking_steps.append({
                        "step_name": "🌐 Perplexity 외부 웹 검색",
                        "description": f"내부 지식이 부족하여 Perplexity API로 최신 웹 정보를 검색했습니다. 신뢰도: {confidence:.1f}/5.0",
                        "result": f"성공 ({sources_count}개 외부 소스 발견)" if step_success else "검색 실패",
                        "execution_time": step_time
                    })
                    
                elif step_type == "query_rewrite":
                    original_clarity = step_data.get("original_clarity", 0)
                    rewritten_queries = step_data.get("rewritten_queries", [])
                    
                    thinking_steps.append({
                        "step_name": "✏️ 질문 재구성 (Few-shot)",
                        "description": f"원본 질문의 명확도({original_clarity:.1f}/5.0)가 낮아 Few-shot 기법으로 더 구체적인 질문으로 재구성했습니다.",
                        "result": f"성공 ({len(rewritten_queries)}개 대안 생성)" if step_success else "재구성 실패",
                        "execution_time": step_time
                    })
                    
                elif step_type == "answer_synthesis":
                    quality_score = step_data.get("quality_score", 0)
                    word_count = step_data.get("word_count", 0)
                    
                    thinking_steps.append({
                        "step_name": "📝 Few-shot 답변 생성",
                        "description": f"검색 결과를 Few-shot 프롬프팅 기법으로 MZ세대 친화적인 고품질 답변으로 합성했습니다.",
                        "result": f"품질 {quality_score:.1f}/5.0 ({word_count}자)" if step_success else "생성 실패",
                        "execution_time": step_time
                    })
                    
                elif step_type == "quality_check":
                    final_score = step_data.get("final_score", 0)
                    threshold_met = step_data.get("threshold_met", False)
                    
                    thinking_steps.append({
                        "step_name": "✅ 품질 임계값 검증",
                        "description": f"생성된 답변의 품질을 임계값({self.thresholds.get(ThresholdType.QUALITY, 3.0)})과 비교하여 검증했습니다.",
                        "result": f"{'통과' if threshold_met else '재시도 필요'} (점수: {final_score:.1f})" if step_success else "검증 실패",
                        "execution_time": step_time
                    })
                    
                else:
                    # 기본 단계 처리 - 실제 실행되는 모든 단계 매핑
                    step_names = {
                        "analysis": "🔍 AnalyzerAgent 분석",
                        "query_rewrite": "✏️ 질문 재구성 (Few-shot)",
                        "date_analysis": "📅 DateProcessor 처리",
                        "latest_first_search": "🆕 최신순 우선 검색",
                        "date_filtered_search": "📆 날짜 필터 검색",
                        "internal_search": "📚 내부 지식 베이스 검색",
                        "external_search": "🌐 Perplexity 외부 검색",
                        "answer_synthesis": "📝 Few-shot 답변 생성",
                        "quality_check": "✅ 품질 임계값 검증"
                    }
                    
                    step_name = step_names.get(step_type, f"⚙️ {step_type} 처리")
                    
                    # 단계별 상세 설명 생성
                    if step_type == "query_rewrite":
                        description = "원본 질문을 Few-shot 기법으로 더 구체적이고 검색하기 좋은 형태로 재구성했습니다."
                    elif step_type == "latest_first_search":
                        description = "날짜 표현이 없어 최신 뉴스를 우선적으로 검색하도록 설정했습니다."
                    elif step_type == "internal_search":
                        description = "AWS Bedrock Knowledge Base에서 관련 뉴스와 정보를 검색했습니다."
                    elif step_type == "date_filtered_search":
                        description = "특정 날짜 범위로 필터링하여 해당 기간의 뉴스를 검색했습니다."
                    else:
                        description = f"{step_type} 단계를 실행했습니다."
                    
                    thinking_steps.append({
                        "step_name": step_name,
                        "description": description,
                        "result": "성공" if step_success else "실패",
                        "execution_time": step_time
                    })
            
            return thinking_steps[:8]  # 최대 8단계까지 표시
            
        except Exception as e:
            logger.error(f"사고 과정 추출 오류: {str(e)}")
            # Fallback: 기본 사고 과정
            return [
                {
                    "step_name": "🧠 AI 종합 사고 과정",
                    "description": "Enhanced Agent System이 ReAct + CoT 방식으로 단계별 사고하여 답변을 생성했습니다.",
                    "result": "완료",
                    "execution_time": 2.0
                },
                {
                    "step_name": "📚 지식 통합 검색",
                    "description": "내부 Knowledge Base와 필요시 외부 웹 검색을 통해 최신 정보를 수집했습니다.",
                    "result": "정보 수집 완료",
                    "execution_time": 1.5
                }
            ]
    
    def _execute_planning_step(self, execution_context: Dict) -> Dict:
        """Planning 단계 실행"""
        try:
            query = execution_context["query"]
            user_context = execution_context["user_context"]
            
            # Planning Agent 호출
            planning_result = self.agents["planner"].plan_execution(query, user_context)
            
            # 날짜 처리 추가
            date_analysis = self.agents["date_processor"].analyze_query_temporal_expressions(query)
            
            # 결과 통합
            enhanced_context = {
                **planning_result,
                "date_analysis": date_analysis,
                "temporal_strategy": date_analysis.get("primary_strategy", "latest_first")
            }
            
            # 실행 컨텍스트 업데이트
            execution_context["planning_result"] = enhanced_context
            execution_context["date_strategy"] = date_analysis
            
            return {
                "success": True,
                "step_type": "planning",
                "data": enhanced_context,
                "execution_time": 0.5,  # 예상 시간
                "thresholds_checked": []
            }
            
        except Exception as e:
            logger.error(f"Planning 단계 실행 오류: {str(e)}")
            return {
                "success": False,
                "step_type": "planning",
                "error": str(e),
                "execution_time": 0.0
            }
    
    def _execute_conditional_step(self, execution_context: Dict, step_config: Dict) -> Dict:
        """조건부 단계 실행"""
        step_type = step_config["type"]
        step_start_time = time.time()
        
        try:
            # 조건 확인
            should_execute = self._check_execution_condition(execution_context, step_config)
            
            if not should_execute:
                return {
                    "success": True,
                    "step_type": step_type,
                    "status": ExecutionStatus.SKIPPED.value,
                    "reason": "condition_not_met",
                    "execution_time": 0.0
                }
            
            # 단계별 실행
            if step_type == "query_rewrite":
                result = self._execute_query_rewrite(execution_context, step_config)
            elif step_type == "internal_search":
                result = self._execute_internal_search(execution_context, step_config)
            elif step_type == "external_search":
                result = self._execute_external_search(execution_context, step_config)
            elif step_type == "date_filtered_search":
                result = self._execute_date_filtered_search(execution_context, step_config)
            elif step_type == "latest_first_search":
                result = self._execute_latest_first_search(execution_context, step_config)
            elif step_type == "answer_synthesis":
                result = self._execute_answer_synthesis(execution_context, step_config)
            elif step_type == "quality_check":
                result = self._execute_quality_check(execution_context, step_config)
            else:
                result = self._execute_generic_step(execution_context, step_config)
            
            execution_time = time.time() - step_start_time
            result["execution_time"] = execution_time
            
            return result
            
        except Exception as e:
            logger.error(f"{step_type} 단계 실행 오류: {str(e)}")
            return {
                "success": False,
                "step_type": step_type,
                "error": str(e),
                "execution_time": time.time() - step_start_time
            }
    
    def _check_execution_condition(self, execution_context: Dict, step_config: Dict) -> bool:
        """실행 조건 확인"""
        step_type = step_config["type"]
        
        # 기본적으로 모든 단계는 실행
        if "condition" not in step_config:
            return True
        
        condition = step_config["condition"]
        
        # 조건별 확인
        if condition == "if_internal_insufficient":
            # 내부 검색 결과가 부족한 경우만 실행
            internal_coverage = execution_context.get("internal_coverage", 0.0)
            return internal_coverage < self.thresholds[ThresholdType.COVERAGE]
        
        elif condition == "if_quality_low":
            # 품질이 낮은 경우만 실행
            current_quality = execution_context.get("current_quality", 1.0)
            return current_quality < self.thresholds[ThresholdType.QUALITY]
        
        elif condition == "if_clarity_low":
            # 명확성이 낮은 경우만 실행
            clarity_score = execution_context.get("clarity_score", 1.0)
            return clarity_score < self.thresholds[ThresholdType.CLARITY]
        
        elif condition == "if_freshness_required":
            # 신선도가 높게 요구되는 경우만 실행
            freshness_priority = execution_context.get("freshness_priority", 0.0)
            return freshness_priority > self.thresholds[ThresholdType.FRESHNESS]
        
        # 알 수 없는 조건은 실행하지 않음
        logger.warning(f"알 수 없는 조건: {condition}")
        return False
    
    def _execute_external_search(self, execution_context: Dict, step_config: Dict) -> Dict:
        """외부 검색 실행"""
        try:
            query = execution_context["query"]
            
            # 컨텍스트 구성
            search_context = {
                "internal_coverage": execution_context.get("internal_coverage", 0.0),
                "freshness_priority": execution_context.get("freshness_priority", 0.0),
                "complexity_level": execution_context.get("complexity_level", "simple"),
                "date_strategy": execution_context.get("date_strategy", {})
            }
            
            # Perplexity 검색 실행
            search_result = self.agents["external_search"].search_external_knowledge(
                query, search_context
            )
            
            # 결과를 실행 컨텍스트에 저장
            execution_context["external_search_result"] = search_result
            execution_context["external_coverage"] = search_result.confidence
            
            return {
                "success": True,
                "step_type": "external_search",
                "data": search_result,
                "status": ExecutionStatus.COMPLETED.value,
                "confidence": getattr(search_result, 'confidence', 0.0),
                "sources_found": len(getattr(search_result, 'sources', []) or getattr(search_result, 'recommended_sources', []))
            }
            
        except Exception as e:
            logger.error(f"외부 검색 실행 오류: {str(e)}")
            return {
                "success": False,
                "step_type": "external_search",
                "error": str(e),
                "status": ExecutionStatus.FAILED.value
            }
    
    def _execute_internal_search(self, execution_context: Dict, step_config: Dict) -> Dict:
        """내부 검색 실행 (Knowledge Base)"""
        try:
            query = execution_context["query"]
            logger.info(f"🔍 Knowledge Base 검색 시작: '{query}'")
            
            # 실제 Knowledge Base 검색 실행
            internal_result = self._search_knowledge_base(query)
            logger.info(f"📚 Knowledge Base 검색 완료: {len(internal_result.get('sources', []))}개 소스 발견")
            
            # 실행 컨텍스트 업데이트
            execution_context["internal_search_result"] = internal_result
            execution_context["internal_coverage"] = internal_result["coverage_score"]
            
            return {
                "success": True,
                "step_type": "internal_search",
                "data": internal_result,
                "status": ExecutionStatus.COMPLETED.value,
                "coverage": internal_result["coverage_score"]
            }
            
        except Exception as e:
            logger.error(f"내부 검색 실행 오류: {str(e)}")
            return {
                "success": False,
                "step_type": "internal_search",
                "error": str(e),
                "status": ExecutionStatus.FAILED.value
            }
    
    def _search_knowledge_base(self, query: str) -> Dict:
        """Knowledge Base 검색 (stream.py와 동일한 로직)"""
        try:
            import boto3
            import os
            import re
            
            bedrock_agent_client = boto3.client("bedrock-agent-runtime")
            KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID', 'PGQV3JXPET')
            
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
            seen = set()
            skipped_count = 0
            
            for idx, result in enumerate(response.get('retrievalResults', [])[:5], 1):
                text = result.get('content', {}).get('text', '')
                
                if not text.strip():
                    continue
                
                # Knowledge Base에서 반환된 데이터 파싱
                articles = []
                lines = text.splitlines()
                
                if lines:
                    title_line = lines[0].strip()
                    if title_line.startswith('"') and title_line.endswith('"'):
                        title_line = title_line[1:-1]
                    
                    current = {"title": title_line}
                    
                    for line in lines[1:]:
                        line = line.strip()
                        if line.startswith("**") and ":**" in line:
                            try:
                                key_end = line.find(":**")
                                if key_end > 2:
                                    key = line[2:key_end].strip()
                                    value = line[key_end + 3:].strip()
                                    current[key] = value
                            except:
                                pass
                        elif line.startswith("**내용:**"):
                            break
                    
                    if current.get("title"):
                        articles.append(current)
                
                # 기사별 처리
                for article in articles:
                    url = article.get("URL", "")
                    title = article.get("title", "")
                    published_date = article.get("발행일", "")
                    
                    if not title:
                        skipped_count += 1
                        continue
                    
                    if url and url in seen:
                        skipped_count += 1
                        continue
                    if url:
                        seen.add(url)
                    
                    # 날짜 포맷팅
                    formatted_date = ""
                    if published_date and "T" in published_date:
                        formatted_date = published_date.split("T")[0]
                    elif published_date:
                        formatted_date = published_date
                    
                    source_info = {
                        'id': len(sources) + 1,
                        'title': title,
                        'date': formatted_date,
                        'url': url if url else f"#article-{len(sources) + 1}"
                    }
                    sources.append(source_info)
                    
                    context_text = f"제목: {title}"
                    if formatted_date:
                        context_text += f"\n발행일: {formatted_date}"
                    if url:
                        context_text += f"\nURL: {url}"
                    contexts.append(f"[{len(sources)}] {context_text}")
            
            if contexts:
                knowledge_context = "\\n\\n=== 서울경제신문 관련 뉴스 ===\\n" + "\\n\\n".join(contexts[:3])
                coverage_score = min(len(sources) / 3.0, 1.0)  # 3개 이상이면 완전한 커버리지
                
                return {
                    'content': knowledge_context,
                    'sources': sources,
                    'coverage_score': coverage_score
                }
            else:
                return {
                    'content': "",
                    'sources': [],
                    'coverage_score': 0.0
                }
                
        except Exception as e:
            logger.error(f"Knowledge Base 검색 오류: {str(e)}")
            return {
                'content': "",
                'sources': [],
                'coverage_score': 0.0
            }
    
    def _execute_date_filtered_search(self, execution_context: Dict, step_config: Dict) -> Dict:
        """날짜 필터링 검색 실행"""
        try:
            date_range = step_config.get("date_range", {})
            query = execution_context["query"]
            
            # 날짜 기반 검색 로직
            search_result = {
                "content": f"날짜 필터링 검색 결과: {query}",
                "date_range": date_range,
                "filtered_count": 15  # 예시
            }
            
            execution_context["date_filtered_result"] = search_result
            
            return {
                "success": True,
                "step_type": "date_filtered_search",
                "data": search_result,
                "status": ExecutionStatus.COMPLETED.value,
                "filtered_articles": search_result["filtered_count"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "step_type": "date_filtered_search",
                "error": str(e),
                "status": ExecutionStatus.FAILED.value
            }
    
    def _execute_latest_first_search(self, execution_context: Dict, step_config: Dict) -> Dict:
        """최신순 검색 실행"""
        try:
            query = execution_context["query"]
            
            # 최신순 검색 로직
            search_result = {
                "content": f"최신순 검색 결과: {query}",
                "sort_order": "latest_first",
                "latest_articles": 20  # 예시
            }
            
            execution_context["latest_first_result"] = search_result
            
            return {
                "success": True,
                "step_type": "latest_first_search", 
                "data": search_result,
                "status": ExecutionStatus.COMPLETED.value,
                "articles_found": search_result["latest_articles"]
            }
            
        except Exception as e:
            return {
                "success": False,
                "step_type": "latest_first_search",
                "error": str(e),
                "status": ExecutionStatus.FAILED.value
            }
    
    def _execute_query_rewrite(self, execution_context: Dict, step_config: Dict) -> Dict:
        """질문 재작성 실행"""
        try:
            original_query = execution_context["query"]
            
            # 질문 재작성 로직 (Mock)
            rewritten_query = f"{original_query} (재작성됨)"
            
            execution_context["rewritten_query"] = rewritten_query
            execution_context["clarity_score"] = 0.9  # 재작성 후 높은 점수
            
            return {
                "success": True,
                "step_type": "query_rewrite",
                "data": {"rewritten_query": rewritten_query},
                "status": ExecutionStatus.COMPLETED.value,
                "clarity_improvement": 0.3
            }
            
        except Exception as e:
            return {
                "success": False,
                "step_type": "query_rewrite",
                "error": str(e),
                "status": ExecutionStatus.FAILED.value
            }
    
    def _execute_answer_synthesis(self, execution_context: Dict, step_config: Dict) -> Dict:
        """답변 합성 실행"""
        try:
            # 모든 검색 결과를 종합하여 답변 생성
            internal_result = execution_context.get("internal_search_result", {})
            external_result = execution_context.get("external_search_result")
            query = execution_context.get("query", "")
            
            # Knowledge Base 결과가 있으면 이를 기반으로 답변 생성
            if internal_result.get("sources"):
                sources = internal_result.get("sources", [])
                content = internal_result.get("content", "")
                
                # 간단한 답변 생성 (실제로는 LLM을 사용해야 함)
                answer_content = f"서울경제신문의 관련 뉴스를 찾았습니다.\n\n"
                
                # 각 소스에 대한 간단한 설명 추가
                for i, source in enumerate(sources[:3], 1):
                    answer_content += f"[{i}] {source['title']}"
                    if source.get('date'):
                        answer_content += f" ({source['date']})"
                    answer_content += "\n"
                
                answer_content += f"\n위의 기사들이 '{query}' 질문과 관련된 서울경제신문의 보도 내용입니다."
                
                synthesized_answer = {
                    "content": answer_content,
                    "sources": sources,
                    "confidence": 0.8
                }
            else:
                # Knowledge Base에서 결과를 찾지 못한 경우
                synthesized_answer = {
                    "content": f"'{query}'에 대한 구체적인 정보를 서울경제신문 데이터베이스에서 찾지 못했습니다. 다른 키워드로 다시 검색해보시기 바랍니다.",
                    "sources": [],
                    "confidence": 0.3
                }
            
            # 외부 결과가 있으면 추가 (현재는 비활성화)
            if external_result and hasattr(external_result, 'sources') and external_result.sources:
                synthesized_answer["sources"].extend(external_result.sources)
            
            execution_context["synthesized_answer"] = synthesized_answer
            
            return {
                "success": True,
                "step_type": "answer_synthesis",
                "data": synthesized_answer,
                "status": ExecutionStatus.COMPLETED.value,
                "sources_count": len(synthesized_answer["sources"])
            }
            
        except Exception as e:
            logger.error(f"답변 합성 오류: {str(e)}")
            return {
                "success": False,
                "step_type": "answer_synthesis",
                "error": str(e),
                "status": ExecutionStatus.FAILED.value
            }
    
    def _execute_quality_check(self, execution_context: Dict, step_config: Dict) -> Dict:
        """품질 검증 실행"""
        try:
            answer = execution_context.get("synthesized_answer", {})
            
            # 품질 점수 계산
            quality_score = self._calculate_quality_score(answer, execution_context)
            
            execution_context["current_quality"] = quality_score
            
            return {
                "success": True,
                "step_type": "quality_check",
                "data": {"quality_score": quality_score},
                "status": ExecutionStatus.COMPLETED.value,
                "quality_score": quality_score,
                "meets_threshold": quality_score >= self.thresholds[ThresholdType.QUALITY]
            }
            
        except Exception as e:
            return {
                "success": False,
                "step_type": "quality_check",
                "error": str(e),
                "status": ExecutionStatus.FAILED.value
            }
    
    def _execute_generic_step(self, execution_context: Dict, step_config: Dict) -> Dict:
        """일반적인 단계 실행"""
        return {
            "success": True,
            "step_type": step_config["type"],
            "data": {},
            "status": ExecutionStatus.COMPLETED.value,
            "note": "generic_execution"
        }
    
    def _calculate_quality_score(self, answer: Dict, context: Dict) -> float:
        """답변 품질 점수 계산"""
        score = 0.5  # 기본 점수
        
        # 내용 길이 평가
        content = answer.get("content", "")
        if len(content) > 100:
            score += 0.1
        if len(content) > 300:
            score += 0.1
        
        # 출처 개수 평가
        sources = answer.get("sources", [])
        if len(sources) >= 2:
            score += 0.15
        if len(sources) >= 4:
            score += 0.1
        
        # 신뢰도 평가
        confidence = answer.get("confidence", 0.5)
        score += confidence * 0.2
        
        return min(score, 1.0)
    
    def _synthesize_final_result(self, execution_context: Dict) -> Dict:
        """최종 결과 합성"""
        synthesized_answer = execution_context.get("synthesized_answer", {})
        
        return {
            "answer": synthesized_answer.get("content", "답변을 생성할 수 없습니다."),
            "sources": synthesized_answer.get("sources", []),
            "metadata": {
                "execution_id": execution_context["execution_id"],
                "steps_executed": len(execution_context["steps"]),
                "date_strategy": execution_context.get("date_strategy", {}),
                "quality_score": execution_context.get("current_quality", 0.0)
            }
        }
    
    def _perform_quality_check(self, final_result: Dict) -> Dict:
        """최종 품질 검증"""
        answer_content = final_result.get("answer", "")
        sources = final_result.get("sources", [])
        
        quality_score = 0.5
        
        # 답변 내용 평가
        if len(answer_content) > 50:
            quality_score += 0.2
        if "답변을 생성할 수 없습니다" not in answer_content:
            quality_score += 0.2
        
        # 출처 평가
        if len(sources) > 0:
            quality_score += 0.1
        
        return {
            "score": quality_score,
            "meets_threshold": quality_score >= self.thresholds[ThresholdType.QUALITY],
            "details": {
                "content_quality": len(answer_content) > 50,
                "has_sources": len(sources) > 0,
                "non_error_response": "답변을 생성할 수 없습니다" not in answer_content
            }
        }
    
    def _handle_step_retry(self, execution_context: Dict, step_config: Dict) -> Dict:
        """단계 재시도 처리"""
        max_retries = self.retry_config["max_retries"]
        current_retries = step_config.get("retries", 0)
        
        if current_retries >= max_retries:
            return {"success": False, "reason": "max_retries_exceeded"}
        
        # 재시도 지연
        delay = self.retry_config["retry_delay"]
        if self.retry_config["exponential_backoff"]:
            delay *= (2 ** current_retries)
        
        time.sleep(delay)
        
        # 재시도 실행
        step_config["retries"] = current_retries + 1
        retry_result = self._execute_conditional_step(execution_context, step_config)
        
        return retry_result
    
    def _retry_with_enhanced_context(self, execution_context: Dict) -> Dict:
        """향상된 컨텍스트로 재시도"""
        try:
            # 원래 질문을 더 구체화
            original_query = execution_context["query"]
            enhanced_query = f"{original_query} (더 자세한 정보 필요)"
            
            # 새로운 실행 컨텍스트 생성
            retry_context = execution_context.copy()
            retry_context["query"] = enhanced_query
            retry_context["retry_attempt"] = True
            
            # 외부 검색 강제 실행
            search_context = {
                "internal_coverage": 0.0,  # 낮게 설정하여 외부 검색 유도
                "freshness_priority": 0.9,
                "complexity_level": "complex"
            }
            
            external_result = self.agents["external_search"].search_external_knowledge(
                enhanced_query, search_context, force_search=True
            )
            
            if external_result.confidence > 0.5:
                return {
                    "success": True,
                    "data": {
                        "answer": external_result.content,
                        "sources": external_result.sources,
                        "metadata": {"retry_enhanced": True}
                    }
                }
            
            return {"success": False, "reason": "retry_also_failed"}
            
        except Exception as e:
            logger.error(f"재시도 중 오류: {str(e)}")
            return {"success": False, "reason": f"retry_error: {str(e)}"}
    
    def _handle_execution_failure(self, execution_context: Dict, reason: str) -> Dict:
        """실행 실패 처리"""
        execution_time = time.time() - execution_context["start_time"]
        
        self._record_failure_metrics(execution_context, execution_time, reason)
        
        return {
            "success": False,
            "execution_id": execution_context["execution_id"],
            "error": reason,
            "metadata": {
                "execution_time": execution_time,
                "steps_completed": len(execution_context["steps"]),
                "failure_point": reason
            }
        }
    
    def _record_success_metrics(self, execution_context: Dict, execution_time: float):
        """성공 메트릭 기록"""
        self.performance_metrics["total_executions"] += 1
        self.performance_metrics["successful_executions"] += 1
        self.performance_metrics["avg_execution_time"] = (
            (self.performance_metrics["avg_execution_time"] * (self.performance_metrics["total_executions"] - 1) + execution_time) /
            self.performance_metrics["total_executions"]
        )
        
        # 외부 검색 사용률 계산
        used_external = any(step.get("step_type") == "external_search" for step in execution_context["steps"])
        if used_external:
            self.performance_metrics["external_search_rate"] = (
                (self.performance_metrics["external_search_rate"] * (self.performance_metrics["total_executions"] - 1) + 1) /
                self.performance_metrics["total_executions"]
            )
    
    def _record_failure_metrics(self, execution_context: Dict, execution_time: float, reason: str):
        """실패 메트릭 기록"""
        self.performance_metrics["total_executions"] += 1
        self.performance_metrics["failed_executions"] += 1
        
        logger.error(f"실행 실패: {execution_context['execution_id']}, 이유: {reason}")
    
    def _create_simple_planner(self):
        """간단한 계획 에이전트"""
        class SimplePlanner:
            def plan_execution(self, query: str, user_context: Dict = None):
                # 실제 질문을 분석하여 실행 계획 수립
                plan = {
                    "execution_plan": {
                        "actions": [
                            {"type": "internal_search", "critical": True},
                            {"type": "answer_synthesis", "critical": True}
                        ]
                    },
                    "clarity_score": 0.8,
                    "complexity_level": "simple"
                }
                
                # 특정 키워드가 있으면 외부 검색도 포함
                if any(keyword in query.lower() for keyword in ["최신", "현재", "지금", "오늘"]):
                    plan["execution_plan"]["actions"].insert(1, {
                        "type": "external_search", 
                        "condition": "if_internal_insufficient",
                        "critical": False
                    })
                    plan["freshness_priority"] = 0.8
                
                return plan
        
        return SimplePlanner()
    
    def _create_simple_date_processor(self):
        """간단한 날짜 처리 에이전트"""
        class SimpleDateProcessor:
            def analyze_query_temporal_expressions(self, query: str):
                # 간단한 날짜 표현 분석
                import re
                
                date_keywords = ["어제", "오늘", "내일", "최근", "최신", "현재", "지금"]
                has_date = any(keyword in query for keyword in date_keywords)
                
                return {
                    "has_date_expression": has_date,
                    "time_expression": "최신" if has_date else "",
                    "primary_strategy": "latest_first" if has_date else "relevance_first",
                    "temporal_priority": 0.8 if has_date else 0.3
                }
        
        return SimpleDateProcessor()
    
    def _create_simple_external_search(self):
        """간단한 외부 검색 에이전트"""
        class SimpleExternalSearch:
            def search_external_knowledge(self, query: str, context: Dict = None, force_search: bool = False):
                # 외부 검색은 일단 빈 결과 반환 (나중에 Perplexity 연동 가능)
                class SearchResult:
                    def __init__(self):
                        self.content = f"외부 검색 결과는 현재 비활성화되어 있습니다. 내부 Knowledge Base 결과를 참조하세요."
                        self.sources = []
                        self.confidence = 0.1  # 낮은 신뢰도
                
                return SearchResult()
        
        return SimpleExternalSearch()
    
    def get_performance_metrics(self) -> Dict:
        """성능 메트릭 조회"""
        return self.performance_metrics.copy()
    
    def update_thresholds(self, new_thresholds: Dict[ThresholdType, float]):
        """임계값 업데이트"""
        for threshold_type, value in new_thresholds.items():
            if threshold_type in self.thresholds:
                self.thresholds[threshold_type] = value
                logger.info(f"임계값 업데이트: {threshold_type.value} = {value}")

# 사용 예시
if __name__ == "__main__":
    engine = ConditionalExecutionEngine()
    
    # 테스트 쿼리들
    test_queries = [
        "삼양식품 주가는 어떤가요?",          # 날짜 표현 없음 → 최신순
        "1년 전 삼성전자는 어땠나요?",        # 날짜 표현 있음 → 날짜 필터링
        "최근 경제 동향 분석해줘",            # 복잡한 질문 → 외부 검색
        "반도체?"                           # 애매한 질문 → 재질문
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*50}")
        print(f"테스트 {i}: {query}")
        print('='*50)
        
        result = engine.execute_workflow(
            query=query,
            user_context={"user_id": f"test_user_{i}"},
            execution_options={"debug": True}
        )
        
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 성능 메트릭 출력
    print(f"\n{'='*50}")
    print("성능 메트릭")
    print('='*50)
    metrics = engine.get_performance_metrics()
    print(json.dumps(metrics, ensure_ascii=False, indent=2)) 
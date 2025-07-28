"""
Smart Query Router - 조건부 분기 기반 지능형 질문 라우팅 시스템
- 날짜 표현 감지 → 해당 기간 필터링 검색
- 애매한 질문 → Perplexity API 우선 검색
- 명확한 질문 → 직접 내부 검색
- 날짜 없음 → 최신순 우선 검색
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# 기존 에이전트들 Import
from agents.analyzer_agent import AnalyzerAgent
from date_intelligence.date_processor import DateIntelligenceProcessor
from external_search.perplexity_integration import PerplexitySearchAgent
from agents.search_agent import SearchAgent
from agents.synthesizer_agent import SynthesizerAgent

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class SmartQueryRouter:
    """
    조건부 분기 기반 지능형 질문 라우팅 시스템
    """
    
    def __init__(self):
        """라우터 초기화"""
        try:
            # 에이전트들 초기화
            self.analyzer_agent = AnalyzerAgent()
            self.date_processor = DateIntelligenceProcessor()
            self.perplexity_agent = PerplexitySearchAgent()
            self.search_agent = SearchAgent()
            self.synthesizer_agent = SynthesizerAgent()
            
            # 임계값 설정
            self.clarity_threshold = 0.6  # 명확성 임계값
            self.perplexity_enabled = bool(os.getenv('PERPLEXITY_API_KEY'))
            
            logger.info("🎯 SmartQueryRouter 초기화 완료")
            logger.info(f"   - Perplexity API: {'활성화' if self.perplexity_enabled else '비활성화'}")
            logger.info(f"   - 명확성 임계값: {self.clarity_threshold}")
            
        except Exception as e:
            logger.error(f"SmartQueryRouter 초기화 실패: {str(e)}")
            raise
    
    def route_and_execute(self, query: str, context: Dict = None) -> Dict:
        """
        메인 라우팅 및 실행 함수
        """
        start_time = time.time()
        
        try:
            # ⭐ STEP 0: 가장 먼저 날짜 컨텍스트 설정 (사용자 제안 구현) ⭐
            from utils.date_context_manager import get_date_context_manager
            
            date_context_manager = get_date_context_manager()
            date_context = date_context_manager.get_date_context()
            
            logger.info(f"📅 날짜 컨텍스트 설정 완료: {date_context['현재_날짜_문자열']}")
            logger.info(f"   - 현재 년도: {date_context['현재_년도']}년")
            logger.info(f"   - 1년 전: {date_context['1년_전_년도']}년")
            
            # 실행 컨텍스트 생성 (날짜 정보 포함)
            execution_context = {
                "query": query,
                "start_time": start_time,
                "context": context or {},
                "date_context": date_context,  # 🎯 모든 에이전트가 사용할 날짜 정보
                "routing_decisions": [],
                "execution_steps": []
            }
            
            logger.info(f"🎯 SmartQueryRouter 실행 시작: '{query}'")
            
            # Step 1: 종합적 질문 분석 (날짜 컨텍스트 포함)
            analysis_result = self._analyze_query_comprehensive(query, execution_context)
            
            # Step 2: 라우팅 결정
            routing_decision = self._make_routing_decision(analysis_result, execution_context)
            
            # Step 3: 선택된 경로 실행
            execution_result = self._execute_selected_route(routing_decision, execution_context)
            
            # Step 4: 최종 답변 합성
            final_result = self._synthesize_final_answer(execution_result, execution_context)
            
            # 실행 시간 계산
            total_time = time.time() - start_time
            
            logger.info(f"✅ SmartQueryRouter 실행 완료 ({total_time:.2f}초)")
            logger.info(f"   - 라우팅: {routing_decision['route_type']}")
            logger.info(f"   - 성공: {final_result.get('success', False)}")
            
            return {
                "success": True,
                "result": final_result,
                "routing_info": routing_decision,
                "execution_time": total_time,
                "thinking_process": self._generate_thinking_process(execution_context)
            }
            
        except Exception as e:
            logger.error(f"SmartQueryRouter 실행 오류: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    def _analyze_query_comprehensive(self, query: str, context: Dict) -> Dict:
        """종합적 질문 분석"""
        logger.info("🔍 종합적 질문 분석 시작")
        
        try:
            # 1. 기본 분석 (AnalyzerAgent) - 날짜 컨텍스트 전달
            basic_analysis = self.analyzer_agent.analyze_query(
                query, 
                context.get("context", {}), 
                context.get("date_context")  # 🎯 날짜 컨텍스트 전달
            )
            
            # 2. 날짜 분석 (DateIntelligenceProcessor)  
            date_analysis = self.date_processor.analyze_query_temporal_expressions(query)
            
            # 3. 종합 분석 결과
            comprehensive_result = {
                "query": query,
                "clarity_score": basic_analysis.clarity_score,
                "category": basic_analysis.category,
                "entities": basic_analysis.entities,
                "temporal_info": basic_analysis.temporal_info,
                "date_expressions": date_analysis.get("detected_expressions", {}),
                "calculated_ranges": date_analysis.get("calculated_ranges", []),
                "has_date_expression": bool(date_analysis.get("detected_expressions")),
                "needs_clarification": basic_analysis.needs_clarification,
                "confidence": basic_analysis.confidence
            }
            
            context["execution_steps"].append({
                "step": "comprehensive_analysis",
                "result": "완료",
                "details": f"명확성: {basic_analysis.clarity_score:.2f}, 날짜표현: {comprehensive_result['has_date_expression']}"
            })
            
            logger.info(f"🔍 분석 완료 - 명확성: {basic_analysis.clarity_score:.2f}, 날짜: {comprehensive_result['has_date_expression']}")
            return comprehensive_result
            
        except Exception as e:
            logger.error(f"종합 분석 오류: {str(e)}")
            raise
    
    def _make_routing_decision(self, analysis: Dict, context: Dict) -> Dict:
        """라우팅 결정 로직 - 사용자 요구사항 반영"""
        logger.info("🧭 라우팅 결정 시작")
        
        query = analysis["query"]
        clarity_score = analysis["clarity_score"]
        has_date_expression = analysis["has_date_expression"]
        
        # 🎯 사용자 요구사항에 따른 조건부 분기
        
        # 조건 0: 날짜 메타 질문 ("오늘의 날짜", "현재 날짜", "지금 몇 시")
        if self._is_date_meta_question(query):
            route_decision = {
                "route_type": "date_meta_response",
                "reason": "날짜/시간 메타 정보 질문",
                "priority": "highest",
                "response_type": "direct_system_info"
            }
            logger.info(f"📅 날짜 메타 질문 감지: {query}")
        
        # 조건 1: 날짜 표현이 있는 경우 ("어제", "10년 전", "오늘" 등)
        elif has_date_expression:
            route_decision = {
                "route_type": "date_filtered_search",
                "reason": "날짜 표현 감지됨",
                "priority": "high",
                "date_info": analysis["date_expressions"],
                "calculated_ranges": analysis["calculated_ranges"]
            }
            logger.info(f"📅 날짜 필터링 검색 선택: {analysis['date_expressions']}")
        
        # 조건 2: 애매한 질문 ("삼성전자", "주가" 등 단순 키워드)
        elif clarity_score < self.clarity_threshold:
            if self.perplexity_enabled:
                route_decision = {
                    "route_type": "clarity_enhancement_flow",
                    "reason": f"명확성 부족 (점수: {clarity_score:.2f})",
                    "priority": "medium",
                    "enhancement_method": "perplexity_first"
                }
                logger.info(f"❓ 명확성 향상 플로우 선택 (Perplexity 우선): {clarity_score:.2f}")
            else:
                route_decision = {
                    "route_type": "direct_internal_search",
                    "reason": "Perplexity 비활성화, 직접 검색",
                    "priority": "low",
                    "fallback": True
                }
                logger.info("❓ Perplexity 비활성화로 직접 검색 선택")
        
        # 조건 3: 명확한 질문
        else:
            route_decision = {
                "route_type": "direct_internal_search",
                "reason": f"명확한 질문 (점수: {clarity_score:.2f})",
                "priority": "high",
                "latest_first": not has_date_expression  # 날짜 없으면 최신순 우선
            }
            logger.info(f"✅ 직접 내부 검색 선택: {clarity_score:.2f}")
        
        # 라우팅 결정 기록
        context["routing_decisions"].append(route_decision)
        context["execution_steps"].append({
            "step": "routing_decision",
            "result": route_decision["route_type"],
            "details": route_decision["reason"]
        })
        
        return route_decision
    
    def _execute_selected_route(self, routing_decision: Dict, context: Dict) -> Dict:
        """선택된 라우팅 경로 실행"""
        route_type = routing_decision["route_type"]
        logger.info(f"🚀 라우팅 실행: {route_type}")
        
        try:
            if route_type == "date_filtered_search":
                return self._execute_date_filtered_search(routing_decision, context)
            elif route_type == "clarity_enhancement_flow":
                return self._execute_clarity_enhancement_flow(routing_decision, context)
            elif route_type == "direct_internal_search":
                return self._execute_direct_internal_search(routing_decision, context)
            elif route_type == "date_meta_response":
                return self._execute_date_meta_response(routing_decision, context)
            else:
                raise ValueError(f"알 수 없는 라우팅 타입: {route_type}")
                
        except Exception as e:
            logger.error(f"라우팅 실행 오류 ({route_type}): {str(e)}")
            # Fallback to direct search
            return self._execute_direct_internal_search({"route_type": "fallback"}, context)
    
    def _execute_date_filtered_search(self, routing_decision: Dict, context: Dict) -> Dict:
        """날짜 필터링된 검색 실행"""
        logger.info("📅 날짜 필터링 검색 실행")
        
        try:
            query = context["query"]
            date_ranges = routing_decision.get("calculated_ranges", [])
            
            # 날짜 범위가 있으면 해당 기간으로 필터링
            search_params = {
                "query": query,
                "date_filter": True,
                "date_ranges": date_ranges,
                "sort_order": "relevance_with_date"
            }
            
            # SearchAgent로 날짜 필터링된 검색 실행 (날짜 컨텍스트 전달)
            search_result = self.search_agent.search_comprehensive(
                query=query,
                search_strategy="date_filtered",
                temporal_info={"date_ranges": date_ranges},
                context=context["context"],
                date_context=context.get("date_context")  # 🎯 날짜 컨텍스트 전달
            )
            
            # CombinedSearchResult 객체에서 안전하게 속성 추출
            sources = getattr(search_result, 'sources', []) or getattr(search_result, 'recommended_sources', [])
            metadata = getattr(search_result, 'metadata', {})
            success = getattr(search_result, 'success', False)
            
            context["execution_steps"].append({
                "step": "date_filtered_search",
                "result": "완료" if success else "실패", 
                "details": f"날짜 범위: {len(date_ranges)}개, 결과: {len(sources)}개"
            })
            
            logger.info(f"📅 날짜 필터링 검색 완료: {len(sources)}개 결과")
            return {
                "search_type": "date_filtered",
                "sources": sources,
                "metadata": metadata,
                "success": success
            }
            
        except Exception as e:
            logger.error(f"날짜 필터링 검색 오류: {str(e)}")
            # Fallback to direct search
            return self._execute_direct_internal_search({"route_type": "fallback"}, context)
    
    def _execute_clarity_enhancement_flow(self, routing_decision: Dict, context: Dict) -> Dict:
        """애매한 질문 명확성 향상 플로우 (Perplexity 우선)"""
        logger.info("❓ 명확성 향상 플로우 실행 (Perplexity 우선)")
        
        try:
            query = context["query"]
            
            # Step 1: Perplexity로 컨텍스트 파악
            logger.info(f"🌐 Perplexity로 '{query}' 컨텍스트 분석 중...")
            perplexity_result = self.perplexity_agent.search_with_caching(
                f"{query} 최신 뉴스 정보",
                context
            )
            
            # Step 2: Perplexity 결과를 바탕으로 검색 쿼리 개선
            enhanced_query = query
            enhanced_context = {}
            
            if perplexity_result and perplexity_result.content:
                perplexity_sources = perplexity_result.sources
                # Perplexity 결과에서 키워드 추출하여 검색 쿼리 개선
                enhanced_context = {
                    "perplexity_context": perplexity_sources[:3],  # 상위 3개 결과만 사용
                    "enhanced_keywords": self._extract_keywords_from_perplexity(perplexity_sources)
                }
                
                logger.info(f"✅ Perplexity 컨텍스트 획득: {len(perplexity_sources)}개 소스")
            else:
                logger.warning("⚠️ Perplexity 결과 없음 - 기본 검색으로 진행")
            
            # Step 3: 내부 검색 실행 (개선된 쿼리로)
            search_result = self.search_agent.execute_search(
                query=enhanced_query,
                context={**context, **enhanced_context}
            )
            
            # Step 4: 결과 합성
            synthesis_context = context.copy()
            synthesis_context.update({
                "perplexity_sources": perplexity_sources if perplexity_result and perplexity_result.content else [],
                "search_strategy": "clarity_enhancement"
            })
            
            synthesis_result = self.synthesizer_agent.synthesize_answer(
                query=query,
                search_results=search_result,
                external_context=perplexity_sources if perplexity_result and perplexity_result.content else [],
                context=synthesis_context
            )
            
            return {
                "success": True,
                "result": synthesis_result,
                "routing_info": {
                    "route_type": "clarity_enhancement_flow",
                    "perplexity_search": {
                        "result": "완료" if perplexity_result and perplexity_result.content else "실패",
                        "details": f"외부 컨텍스트: {len(perplexity_sources) if perplexity_result and perplexity_result.content else 0}개"
                    },
                    "internal_search": {
                        "result": "완료" if hasattr(search_result, 'content') else "실패"
                    }
                },
                "execution_result": search_result,
                "external_context": perplexity_sources if perplexity_result and perplexity_result.content else [],
                "execution_time": time.time() - context["start_time"] # 전체 실행 시간 계산
            }
            
        except Exception as e:
            logger.error(f"명확성 향상 플로우 오류: {str(e)}")
            # Fallback to direct search  
            return self._execute_direct_internal_search({"route_type": "fallback"}, context)
    
    def _execute_direct_internal_search(self, routing_decision: Dict, context: Dict) -> Dict:
        """직접 내부 검색 실행 (최신순 우선)"""
        logger.info("📚 직접 내부 검색 실행")
        
        try:
            query = context["query"]
            latest_first = routing_decision.get("latest_first", True)
            
            # 날짜 언급이 없으면 최신순 우선 검색
            search_strategy = "latest_first" if latest_first else "relevance"
            
            search_result = self.search_agent.search_comprehensive(
                query=query,
                search_strategy=search_strategy,
                temporal_info={"priority": "latest_first"} if latest_first else {},
                context=context["context"],
                date_context=context.get("date_context")  # 🎯 날짜 컨텍스트 전달
            )
            
            context["execution_steps"].append({
                "step": "direct_internal_search",
                "result": "완료" if search_result.success else "실패",
                "details": f"전략: {search_strategy}, 결과: {len(search_result.sources)}개"
            })
            
            # CombinedSearchResult 객체에서 안전하게 속성 추출
            sources = getattr(search_result, 'sources', []) or getattr(search_result, 'recommended_sources', [])
            metadata = getattr(search_result, 'metadata', {})
            success = getattr(search_result, 'success', False)
            
            logger.info(f"📚 직접 내부 검색 완료: {len(sources)}개 결과 ({search_strategy})")
            return {
                "search_type": "direct_internal",
                "sources": sources,
                "metadata": metadata,
                "success": success
            }
            
        except Exception as e:
            logger.error(f"직접 내부 검색 오류: {str(e)}")
            return {
                "search_type": "direct_internal",
                "sources": [],
                "metadata": {"error": str(e)},
                "success": False
            }
    
    def _execute_date_meta_response(self, routing_decision: Dict, context: Dict) -> Dict:
        """날짜/시간 메타 정보 질문에 대한 응답 실행"""
        logger.info("📅 날짜/시간 메타 정보 질문 응답 실행")
        
        try:
            query = context["query"]
            
            # 현재 날짜 및 시간 정보 추출
            current_datetime = datetime.now()
            current_date = current_datetime.strftime("%Y년 %m월 %d일")
            current_time = current_datetime.strftime("%H시 %M분")
            
            # 쿼리에 따라 적절한 응답 생성
            if "오늘의 날짜" in query or "현재 날짜" in query:
                response = f"현재 날짜는 {current_date}입니다."
            elif "지금 몇 시" in query:
                response = f"현재 시간은 {current_time}입니다."
            else:
                response = f"현재 날짜는 {current_date}이고, 시간은 {current_time}입니다."
            
            # SynthesizerAgent로 응답 합성
            synthesis_result = self.synthesizer_agent.synthesize_answer(
                query=query,
                sources=[], # 메타 정보는 소스로 포함하지 않음
                external_context=[],
                context={
                    "search_type": "date_meta_response",
                    "routing_info": context.get("routing_decisions", [])
                }
            )
            
            return {
                "success": True,
                "result": synthesis_result,
                "routing_info": {
                    "route_type": "date_meta_response",
                    "response_type": routing_decision["response_type"]
                },
                "execution_result": {"content": response},
                "external_context": [],
                "execution_time": time.time() - context["start_time"]
            }
            
        except Exception as e:
            logger.error(f"날짜/시간 메타 정보 질문 응답 오류: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": time.time() - context["start_time"]
            }
    
    def _extract_keywords_from_perplexity(self, perplexity_sources: List[Dict]) -> List[str]:
        """Perplexity 결과에서 키워드 추출"""
        keywords = []
        try:
            for source in perplexity_sources[:2]:  # 상위 2개만 사용
                content = source.get("content", "")
                # 간단한 키워드 추출 (실제로는 더 정교한 NLP 가능)
                words = content.split()[:20]  # 처음 20개 단어만
                keywords.extend([word for word in words if len(word) > 2])
            
            return list(set(keywords))[:10]  # 중복 제거 후 상위 10개
        except Exception as e:
            logger.error(f"키워드 추출 오류: {str(e)}")
            return []
    
    def _synthesize_final_answer(self, execution_result: Dict, context: Dict) -> Dict:
        """최종 답변 합성"""
        logger.info("📝 최종 답변 합성 시작")
        
        try:
            query = context["query"]
            
            # CombinedSearchResult 객체에서 올바르게 sources 추출
            if hasattr(execution_result, 'sources'):
                sources = execution_result.sources  # @property 직접 접근
            else:
                sources = execution_result.get("sources", [])  # fallback
                
            external_context = execution_result.get("external_context", [])
            
            # SynthesizerAgent로 최종 답변 생성
            synthesis_result = self.synthesizer_agent.synthesize_answer(
                query=query,
                sources=sources,
                external_context=external_context,
                synthesis_context={
                    "search_type": execution_result.get("search_type"),
                    "routing_info": context.get("routing_decisions", [])
                }
            )
            
            # SynthesisResult 객체를 딕셔너리로 변환
            if hasattr(synthesis_result, 'answer'):
                result_dict = {
                    "answer": synthesis_result.answer,
                    "sources": synthesis_result.sources,
                    "quality_score": synthesis_result.quality_score,
                    "word_count": synthesis_result.word_count,
                    "confidence": synthesis_result.confidence,
                    "success": True
                }
                
                # 모델 선택 정보를 context에 저장 (사고 과정용)
                if hasattr(synthesis_result, 'metadata') and synthesis_result.metadata:
                    context["model_selection"] = {
                        "selected_model": synthesis_result.metadata.get("selected_model"),
                        "complexity_level": synthesis_result.metadata.get("complexity_level"),
                        "model_priority": synthesis_result.metadata.get("model_priority"),
                        "model_tier": synthesis_result.metadata.get("model_tier")
                    }
            else:
                # 이미 딕셔너리인 경우 (Fallback)
                result_dict = synthesis_result
                result_dict["success"] = True
            
            context["execution_steps"].append({
                "step": "final_synthesis",
                "result": "완료",
                "details": f"답변 길이: {len(result_dict.get('answer', ''))}"
            })
            
            logger.info(f"📝 최종 답변 합성 완료: {len(result_dict.get('answer', ''))}자")
            return result_dict
            
        except Exception as e:
            logger.error(f"최종 답변 합성 오류: {str(e)}")
            return {
                "answer": "죄송합니다. 답변 생성 중 오류가 발생했습니다.",
                "sources": execution_result.get("sources", []),
                "success": False,
                "error": str(e)
            }
    
    def _generate_thinking_process(self, context: Dict) -> List[Dict]:
        """사고 과정 생성 (사용자 요청사항)"""
        thinking_steps = []
        
        try:
            # 라우팅 결정 단계
            if context.get("routing_decisions"):
                decision = context["routing_decisions"][0]
                thinking_steps.append({
                    "step_name": "🧭 Smart Query Routing",
                    "description": f"'{context['query']}'를 분석하여 최적의 처리 경로를 결정했습니다.",
                    "result": f"{decision['route_type']} - {decision['reason']}",
                    "execution_time": 0.5
                })
            
            # 실행 단계들
            for i, step in enumerate(context.get("execution_steps", []), 1):
                step_name_map = {
                    "comprehensive_analysis": "🔍 종합적 질문 분석",
                    "routing_decision": "🧭 라우팅 결정",
                    "date_filtered_search": "📅 날짜 필터링 검색",
                    "perplexity_context_analysis": "🌐 Perplexity 컨텍스트 분석",
                    "enhanced_internal_search": "📚 개선된 내부 검색",
                    "direct_internal_search": "📚 직접 내부 검색",
                    "final_synthesis": "📝 최종 답변 합성"
                }
                
                step_name = step_name_map.get(step["step"], f"⚙️ {step['step']}")
                thinking_steps.append({
                    "step_name": step_name,
                    "description": step.get("details", "처리 완료"),
                    "result": step["result"],
                    "execution_time": 0.8
                })
            
            # APAC 모델 선택 정보 추가
            if context.get("model_selection"):
                model_info = context["model_selection"]
                model_tier = model_info.get("model_tier", "unknown")
                complexity = model_info.get("complexity_level", "medium")
                priority = model_info.get("model_priority", "balance")
                
                tier_name_map = {
                    "fast": "초고속 (1.89초)",
                    "balanced": "균형 (3.22초)", 
                    "high_performance": "고성능 (3.92초)",
                    "advanced": "고급 (4.17초)",
                    "premium": "프리미엄 (4.48초)",
                    "latest": "최신 (5.78초)"
                }
                
                tier_display = tier_name_map.get(model_tier, f"{model_tier}")
                
                thinking_steps.append({
                    "step_name": "🤖 APAC 모델 선택",
                    "description": f"질문 복잡도({complexity})와 우선순위({priority})를 분석하여 최적 Claude 모델을 선택했습니다.",
                    "result": f"Claude {tier_display} (서울 리전)",
                    "execution_time": 0.3
                })
            
            return thinking_steps[:6]  # 최대 6단계만 표시
            
        except Exception as e:
            logger.error(f"사고 과정 생성 오류: {str(e)}")
            return [{
                "step_name": "🎯 Smart Query Router",
                "description": "조건부 분기 기반으로 질문을 지능적으로 처리했습니다.",
                "result": "완료",
                "execution_time": 1.0
            }] 

    def _is_date_meta_question(self, query: str) -> bool:
        """날짜/시간 메타 정보 질문인지 판단"""
        import re
        
        date_meta_patterns = [
            r"오늘.*날짜", r"현재.*날짜", r"지금.*날짜", r"날짜.*무엇", r"날짜.*몇",
            r"몇.*월.*몇.*일", r"현재.*시간", r"지금.*몇.*시", r"오늘.*무슨.*요일",
            r"지금.*년도", r"현재.*년", r"오늘.*며칠"
        ]
        
        query_normalized = query.lower().replace(" ", "")
        
        for pattern in date_meta_patterns:
            if re.search(pattern.replace(".*", ".*?"), query_normalized):
                return True
        
        return False
    
    def _execute_date_meta_response(self, routing_decision: Dict, context: Dict) -> Dict:
        """날짜/시간 메타 정보 직접 응답"""
        from datetime import datetime
        import locale
        
        logger.info("📅 날짜 메타 정보 응답 생성")
        
        try:
            # 한국 시간으로 현재 날짜/시간 생성
            current_time = datetime.now()
            
            # 요일 한글 변환
            weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
            current_weekday = weekdays[current_time.weekday()]
            
            # 질문에 따른 맞춤 답변 생성
            query = context["query"].lower()
            
            if "시간" in query:
                answer = f"현재 시간은 {current_time.strftime('%Y년 %m월 %d일 %H시 %M분')}입니다."
            elif "요일" in query:
                answer = f"오늘은 {current_time.strftime('%Y년 %m월 %d일')} {current_weekday}입니다."
            else:
                answer = f"오늘 날짜는 {current_time.strftime('%Y년 %m월 %d일')} {current_weekday}입니다."
            
            # SynthesisResult 형태로 반환
            from agents.synthesizer_agent import SynthesisResult
            
            synthesis_result = SynthesisResult(
                answer=answer,
                confidence_score=1.0,
                sources_count=0,
                metadata={
                    "response_type": "date_meta",
                    "current_datetime": current_time.isoformat(),
                    "selected_model": context.get("model_id", "system"),
                    "complexity_level": "매우 간단",
                    "model_priority": "시스템 응답",
                    "model_tier": "meta"
                }
            )
            
            return {
                "success": True,
                "result": synthesis_result,
                "routing_info": {
                    "route_type": "date_meta_response",
                    "response_method": "direct_system",
                    "processing_time": "즉시"
                },
                "execution_result": None,
                "external_context": []
            }
            
        except Exception as e:
            logger.error(f"날짜 메타 응답 생성 오류: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "result": {
                    "answer": "날짜 정보 조회 중 오류가 발생했습니다.",
                    "thinking_process": [],
                    "metadata": {}
                }
            } 
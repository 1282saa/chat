"""
통합 검색 에이전트 (SearchAgent)
- 내부 Knowledge Base 검색 + 외부 Perplexity 검색 통합
- S3 메타데이터 활용한 날짜 기반 필터링
- 검색 결과 품질 평가 및 커버리지 분석
- 조건부 외부 검색 실행
"""
import json
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import boto3
import re
from dataclasses import dataclass

logger = logging.getLogger()
logger.setLevel(logging.INFO)

@dataclass
class SearchResult:
    """검색 결과 데이터 클래스"""
    content: str
    sources: List[Dict]
    search_type: str
    coverage_score: float
    confidence: float
    timestamp: str
    metadata: Dict

@dataclass
class CombinedSearchResult:
    """통합 검색 결과"""
    internal_result: Optional[SearchResult]
    external_result: Optional[SearchResult]
    combined_coverage: float
    recommended_sources: List[Dict]
    search_strategy_used: str
    execution_time: float
    success: bool = True  # 검색 성공 여부
    metadata: Dict = None  # 메타데이터 속성 추가
    
    def __post_init__(self):
        """초기화 후 metadata 기본값 설정"""
        if self.metadata is None:
            self.metadata = {
                "search_strategy": self.search_strategy_used,
                "execution_time": self.execution_time,
                "sources_count": len(self.recommended_sources),
                "combined_coverage": self.combined_coverage
            }
    
    @property
    def sources(self) -> List[Dict]:
        """호환성을 위한 sources 속성"""
        return self.recommended_sources

class SearchAgent:
    """
    내부/외부 검색을 통합 처리하는 검색 에이전트
    """
    
    def __init__(self):
        # AWS 클라이언트들
        self.bedrock_agent_client = boto3.client("bedrock-agent-runtime", region_name="ap-northeast-2")
        self.s3_client = boto3.client("s3", region_name="ap-northeast-2")
        
        # 설정값
        self.knowledge_base_id = os.environ.get("KNOWLEDGE_BASE_ID", "PGQV3JXPET")
        self.s3_bucket = os.environ.get("NEWS_BUCKET", "seoul-news-data")
        
        # 임계값 설정
        self.thresholds = {
            "internal_sufficient": 0.8,    # 내부 검색만으로 충분한 기준
            "external_trigger": 0.5,       # 외부 검색 필요 기준
            "coverage_minimum": 0.7,       # 최소 커버리지 요구사항
            "freshness_requirement": 0.8,  # 신선도 요구 시 외부 검색
            "max_sources": 10              # 최대 소스 개수
        }
        
        # S3 메타데이터 설정
        self.s3_date_format = "%Y-%m-%dT%H:%M:%S.%f%z"  # 2025-07-02T00:00:00.000+09:00
        
        # 외부 검색 에이전트 (실제 환경에서는 import)
        self.external_search_agent = None
        self._initialize_external_agent()
        
        # 검색 결과 품질 평가 기준
        self.quality_criteria = {
            "relevance_keywords": ["뉴스", "보도", "발표", "분석", "전망"],
            "reliability_domains": ["sedaily.com", "yonhapnews.co.kr", "chosun.com"],
            "freshness_indicators": ["최근", "오늘", "어제", "이번주"]
        }
    
    def _initialize_external_agent(self):
        """외부 검색 에이전트 초기화"""
        try:
            # 실제 환경에서는 적절한 import 경로 사용
            from external_search.perplexity_integration import PerplexitySearchAgent
            self.external_search_agent = PerplexitySearchAgent()
            logger.info("외부 검색 에이전트 초기화 완료")
        except ImportError:
            logger.warning("외부 검색 에이전트 임포트 실패, Mock 사용")
            self.external_search_agent = self._create_mock_external_agent()
    
    def search_comprehensive(self, 
                            query: str,
                            search_strategy: str,
                            temporal_info: Dict = None,
                            context: Dict = None,
                            date_context: Dict = None) -> CombinedSearchResult:
        """
        통합 검색 메인 함수 (날짜 컨텍스트 활용)
        """
        start_time = datetime.now()
        
        try:
            logger.info(f"통합 검색 시작: {query} (전략: {search_strategy})")
            
            # 날짜 컨텍스트 활용 로그
            if date_context:
                logger.info(f"📅 검색에 날짜 컨텍스트 활용: {date_context['현재_날짜_문자열']}")
            
            # 1. 내부 검색 실행 (날짜 컨텍스트 전달)
            internal_result = self._execute_internal_search(query, temporal_info, context, date_context)
            
            # 2. 커버리지 평가
            coverage_assessment = self._assess_coverage(internal_result, context)
            
            # 3. 외부 검색 필요성 판단
            needs_external = self._should_execute_external_search(
                coverage_assessment, search_strategy, temporal_info
            )
            
            external_result = None
            if needs_external:
                # 4. 외부 검색 실행
                external_result = self._execute_external_search(query, temporal_info, context)
            
            # 5. 결과 통합 및 최적화
            combined_result = self._combine_and_optimize_results(
                internal_result, external_result, search_strategy
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"검색 완료 - 내부: {internal_result.coverage_score:.2f}, "
                       f"외부: {'Y' if external_result else 'N'}, 시간: {execution_time:.2f}s")
            
            return CombinedSearchResult(
                internal_result=internal_result,
                external_result=external_result,
                combined_coverage=combined_result["coverage"],
                recommended_sources=combined_result["sources"],
                search_strategy_used=search_strategy,
                execution_time=execution_time
            )
            
        except Exception as e:
            logger.error(f"통합 검색 중 오류: {str(e)}")
            return self._get_fallback_search_result(query)
    
    def _execute_internal_search(self, 
                                query: str, 
                                temporal_info: Dict = None, 
                                context: Dict = None,
                                date_context: Dict = None) -> SearchResult:
        """
        내부 Knowledge Base 검색 실행
        """
        try:
            # S3 메타데이터 기반 날짜 필터링 준비 (올바른 파라미터 전달)
            date_filter = self._prepare_date_filter(
                date_range=temporal_info, 
                date_context=date_context
            )
            
            # Knowledge Base 검색 요청 구성
            search_request = {
                "knowledgeBaseId": self.knowledge_base_id,
                "retrievalQuery": {
                    "text": query
                },
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {
                        "numberOfResults": 20,  # 충분한 결과 확보
                        "overrideSearchType": "HYBRID"  # 하이브리드 검색
                    }
                }
            }
            
            # 날짜 필터 적용 (메타데이터 기반)
            if date_filter:
                search_request["retrievalConfiguration"]["vectorSearchConfiguration"]["filter"] = date_filter
            
            # Bedrock Knowledge Base 검색 실행
            response = self.bedrock_agent_client.retrieve(**search_request)
            
            # 결과 처리 및 품질 평가
            processed_result = self._process_internal_results(response, query, temporal_info)
            
            return processed_result
            
        except Exception as e:
            logger.error(f"내부 검색 실행 오류: {str(e)}")
            return self._get_empty_search_result("internal", f"내부 검색 오류: {str(e)}")
    
    def _prepare_date_filter(self, date_range: Dict = None, date_context: Dict = None, date_context_manager: Dict = None) -> Dict:
        """
        Knowledge Base 검색용 날짜 필터 준비
        DateContextManager 활용 (사용자 제안 구현)
        """
        if not date_range and not date_context and not date_context_manager:
            return None
        
        try:
            # DateContextManager 활용 (사용자 제안)
            if date_context_manager:
                logger.info(f"📅 DateContextManager를 활용한 날짜 필터 생성")
                # 기본 범위: 최근 30일
                end_date = date_context_manager['현재_시간']
                start_date = end_date - timedelta(days=30)
                logger.info(f"기본 날짜 범위: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
            elif date_range:
                # 기존 date_range 사용
                try:
                    start_date = datetime.fromisoformat(date_range["start_date"].replace('Z', '+00:00'))
                    end_date = datetime.fromisoformat(date_range["end_date"].replace('Z', '+00:00'))
                    logger.info(f"제공된 날짜 범위: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
                except (KeyError, ValueError) as e:
                    logger.warning(f"날짜 파싱 오류: {str(e)}, 기본값 사용")
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=30)
            else:
                # 최종 대안
                end_date = datetime.now()
                start_date = end_date - timedelta(days=30)
                logger.info(f"대안 날짜 범위: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")
        
            # S3 메타데이터 형식으로 변환 (2025-07-02T00:00:00.000+09:00)
            start_str = start_date.strftime("%Y-%m-%dT%H:%M:%S.000+09:00")
            end_str = end_date.strftime("%Y-%m-%dT%H:%M:%S.000+09:00")
            
            # Knowledge Base 메타데이터 필터 구성
            date_filter = {
                "andAll": [
                    {
                        "greaterThanOrEquals": {
                            "key": "published_date",
                            "value": start_str
                        }
                    },
                    {
                        "lessThanOrEquals": {
                            "key": "published_date", 
                            "value": end_str
                        }
                    }
                ]
            }
            
            logger.info(f"✅ 날짜 필터 생성 완료: {start_str} ~ {end_str}")
            return date_filter
            
        except Exception as e:
            logger.error(f"날짜 필터 생성 오류: {str(e)}")
            return None
    
    def _process_internal_results(self, 
                                 bedrock_response: Dict, 
                                 query: str, 
                                 temporal_info: Dict = None) -> SearchResult:
        """
        내부 검색 결과 처리
        """
        try:
            retrieval_results = bedrock_response.get("retrievalResults", [])
            
            if not retrieval_results:
                return self._get_empty_search_result("internal", "검색 결과 없음")
            
            # 결과 정리 및 점수 계산
            processed_sources = []
            total_relevance = 0.0
            content_pieces = []
            
            for i, result in enumerate(retrieval_results[:self.thresholds["max_sources"]]):
                # 메타데이터에서 발행일 정보 추출 (뉴스 서비스 필수)
                metadata = result.get("metadata", {})
                published_date_raw = metadata.get("published_date", "")
                
                # S3 발행일 파싱 (2025-07-02T00:00:00.000+09:00 형식)
                published_date_korean = self._format_published_date(published_date_raw)
                
                # 소스 정보 추출 (발행일 정보 포함)
                source_info = {
                    "index": i + 1,
                    "content": result.get("content", {}).get("text", ""),
                    "score": result.get("score", 0.0),
                    "metadata": metadata,
                    "uri": result.get("location", {}).get("s3Location", {}).get("uri", ""),
                    "relevance": self._calculate_relevance(result.get("content", {}).get("text", ""), query),
                    "published_date_raw": published_date_raw,  # 원본 발행일
                    "published_date_korean": published_date_korean,  # 한국어 형식 발행일
                    "has_date_info": bool(published_date_raw)  # 날짜 정보 존재 여부
                }
                
                processed_sources.append(source_info)
                total_relevance += source_info["relevance"]
                
                # 내용 수집 (요약용)
                if source_info["content"]:
                    content_pieces.append(source_info["content"][:300] + "...")
            
            # 전체 커버리지 계산
            coverage_score = self._calculate_internal_coverage(processed_sources, query, temporal_info)
            
            # 결합된 내용 생성
            combined_content = "\n\n".join(content_pieces[:5])  # 상위 5개만
            
            return SearchResult(
                content=combined_content,
                sources=processed_sources,
                search_type="internal",
                coverage_score=coverage_score,
                confidence=min(total_relevance / len(processed_sources) if processed_sources else 0.0, 1.0),
                timestamp=datetime.now().isoformat(),
                metadata={
                    "total_results": len(retrieval_results),
                    "processed_results": len(processed_sources),
                    "avg_score": sum(s["score"] for s in processed_sources) / len(processed_sources) if processed_sources else 0.0,
                    "has_date_filter": temporal_info is not None and temporal_info.get("has_time_expression", False)
                }
            )
            
        except Exception as e:
            logger.error(f"내부 결과 처리 오류: {str(e)}")
            return self._get_empty_search_result("internal", f"결과 처리 오류: {str(e)}")
    
    def _calculate_relevance(self, content: str, query: str) -> float:
        """
        컨텐츠와 쿼리 간의 관련성 점수 계산
        """
        if not content or not query:
            return 0.0
        
        # 키워드 매칭 점수
        query_keywords = query.lower().split()
        content_lower = content.lower()
        
        keyword_matches = sum(1 for keyword in query_keywords if keyword in content_lower)
        keyword_score = keyword_matches / len(query_keywords) if query_keywords else 0.0
        
        # 품질 지표 점수
        quality_score = 0.0
        for indicator in self.quality_criteria["relevance_keywords"]:
            if indicator in content_lower:
                quality_score += 0.1
        
        # 최종 점수 (0-1)
        final_score = (keyword_score * 0.7) + (min(quality_score, 0.3))
        return min(final_score, 1.0)
    
    def _calculate_internal_coverage(self, 
                                   sources: List[Dict], 
                                   query: str, 
                                   temporal_info: Dict = None) -> float:
        """
        내부 검색 커버리지 계산
        """
        if not sources:
            return 0.0
        
        base_coverage = 0.3  # 기본 점수
        
        # 소스 개수 평가
        if len(sources) >= 5:
            base_coverage += 0.2
        elif len(sources) >= 3:
            base_coverage += 0.1
        
        # 관련성 평가
        avg_relevance = sum(s["relevance"] for s in sources) / len(sources)
        base_coverage += avg_relevance * 0.3
        
        # 신선도 평가
        if temporal_info and temporal_info.get("freshness_priority", 0.0) > 0.7:
            # 최신 정보 요구 시 커버리지 감소 (외부 검색 유도)
            base_coverage *= 0.7
        
        # 날짜 필터링 적용 시 보정
        if temporal_info and temporal_info.get("has_time_expression"):
            base_coverage += 0.1  # 정확한 날짜 범위 검색에 대한 보너스
        
        return min(base_coverage, 1.0)
    
    def _assess_coverage(self, internal_result: SearchResult, context: Dict = None) -> Dict:
        """
        검색 커버리지 평가
        """
        assessment = {
            "internal_coverage": internal_result.coverage_score,
            "confidence": internal_result.confidence,
            "source_count": len(internal_result.sources),
            "content_quality": self._assess_content_quality(internal_result.content),
            "recommendation": "sufficient"  # 기본값
        }
        
        # 추천 결정
        if internal_result.coverage_score < self.thresholds["external_trigger"]:
            assessment["recommendation"] = "needs_external"
        elif internal_result.coverage_score < self.thresholds["internal_sufficient"]:
            assessment["recommendation"] = "consider_external"
        
        # 맥락 기반 조정
        if context:
            freshness_priority = context.get("freshness_priority", 0.0)
            if freshness_priority > self.thresholds["freshness_requirement"]:
                assessment["recommendation"] = "needs_external"
                assessment["reason"] = "high_freshness_requirement"
        
        return assessment
    
    def _assess_content_quality(self, content: str) -> float:
        """
        컨텐츠 품질 평가
        """
        if not content:
            return 0.0
        
        quality_score = 0.5  # 기본 점수
        
        # 길이 평가
        if len(content) > 200:
            quality_score += 0.1
        if len(content) > 500:
            quality_score += 0.1
        
        # 구조 평가
        if "." in content:
            quality_score += 0.1  # 문장 구조
        if any(keyword in content for keyword in self.quality_criteria["relevance_keywords"]):
            quality_score += 0.2  # 뉴스 관련 키워드
        
        return min(quality_score, 1.0)
    
    def _should_execute_external_search(self, 
                                      coverage_assessment: Dict,
                                      search_strategy: str, 
                                      temporal_info: Dict = None) -> bool:
        """
        외부 검색 실행 여부 결정
        """
        # 커버리지 기반 판단
        if coverage_assessment["recommendation"] == "needs_external":
            return True
        
        # 전략 기반 판단
        if search_strategy in ["fresh_content_priority", "multi_source_search"]:
            return True
        
        # 신선도 요구사항 기반 판단
        if temporal_info:
            freshness_priority = temporal_info.get("freshness_priority", 0.0)
            if freshness_priority > self.thresholds["freshness_requirement"]:
                return True
            
            # 날짜 표현이 없는 경우 (최신순 요구)
            if temporal_info.get("search_mode") == "latest_first":
                return True
        
        return False
    
    def _execute_external_search(self, 
                                query: str, 
                                temporal_info: Dict = None, 
                                context: Dict = None) -> Optional[SearchResult]:
        """
        외부 검색 실행
        """
        try:
            if not self.external_search_agent:
                logger.warning("외부 검색 에이전트 없음")
                return None
            
            # 외부 검색 컨텍스트 구성
            search_context = {
                "internal_coverage": context.get("internal_coverage", 0.0) if context else 0.0,
                "freshness_priority": temporal_info.get("freshness_priority", 0.0) if temporal_info else 0.0,
                "complexity_level": context.get("complexity_level", "simple") if context else "simple",
                "date_strategy": temporal_info or {}
            }
            
            # Perplexity 검색 실행
            external_result = self.external_search_agent.search_external_knowledge(
                query, search_context
            )
            
            # SearchResult 형식으로 변환
            return SearchResult(
                content=external_result.content,
                sources=[
                    {
                        "index": i + 1,
                        "title": source.get("title", ""),
                        "url": source.get("url", ""),
                        "snippet": source.get("snippet", ""),
                        "domain": source.get("domain", ""),
                        "relevance": 0.8  # 외부 검색 결과는 기본 높은 관련성
                    }
                    for i, source in enumerate(external_result.sources)
                ],
                search_type="external",
                coverage_score=external_result.confidence,
                confidence=external_result.confidence,
                timestamp=external_result.timestamp,
                metadata={
                    "token_usage": external_result.token_usage,
                    "search_provider": "perplexity",
                    "query_optimized": True
                }
            )
            
        except Exception as e:
            logger.error(f"외부 검색 실행 오류: {str(e)}")
            return None
    
    def _combine_and_optimize_results(self, 
                                    internal_result: SearchResult,
                                    external_result: Optional[SearchResult], 
                                    search_strategy: str) -> Dict:
        """
        내부/외부 검색 결과 통합 및 최적화
        """
        combined_sources = []
        combined_coverage = internal_result.coverage_score
        
        # 내부 검색 결과 추가
        for source in internal_result.sources:
            source["source_type"] = "internal"
            combined_sources.append(source)
        
        # 외부 검색 결과 추가 (있는 경우)
        if external_result:
            for source in external_result.sources:
                source["source_type"] = "external"
                combined_sources.append(source)
            
            # 커버리지 결합 (가중 평균)
            combined_coverage = (internal_result.coverage_score * 0.6 + 
                               external_result.coverage_score * 0.4)
        
        # 소스 우선순위 정렬
        optimized_sources = self._prioritize_sources(combined_sources, search_strategy)
        
        return {
            "sources": optimized_sources[:self.thresholds["max_sources"]],
            "coverage": combined_coverage,
            "source_mix": {
                "internal_count": len([s for s in optimized_sources if s.get("source_type") == "internal"]),
                "external_count": len([s for s in optimized_sources if s.get("source_type") == "external"])
            }
        }
    
    def _prioritize_sources(self, sources: List[Dict], search_strategy: str) -> List[Dict]:
        """
        소스 우선순위 정렬
        """
        def get_priority_score(source):
            score = source.get("relevance", 0.0)
            
            # 전략별 가중치 적용
            if search_strategy == "latest_first_search":
                if source.get("source_type") == "external":
                    score *= 1.2  # 외부 검색 결과 우선
            elif search_strategy == "date_filtered_search":
                if source.get("source_type") == "internal":
                    score *= 1.1  # 내부 검색 결과 우선 (정확한 날짜 필터링)
            
            # 신뢰도 높은 도메인 가중치
            if source.get("domain"):
                for trusted_domain in self.quality_criteria["reliability_domains"]:
                    if trusted_domain in source.get("domain", ""):
                        score *= 1.15
                        break
            
            return score
        
        return sorted(sources, key=get_priority_score, reverse=True)
    
    def _get_empty_search_result(self, search_type: str, reason: str) -> SearchResult:
        """빈 검색 결과 생성"""
        return SearchResult(
            content=f"검색 결과 없음: {reason}",
            sources=[],
            search_type=search_type,
            coverage_score=0.0,
            confidence=0.0,
            timestamp=datetime.now().isoformat(),
            metadata={"error": reason}
        )
    
    def _get_fallback_search_result(self, query: str) -> CombinedSearchResult:
        """Fallback 검색 결과"""
        fallback_internal = SearchResult(
            content=f"{query}에 대한 검색 중 오류가 발생했습니다.",
            sources=[],
            search_type="fallback",
            coverage_score=0.0,
            confidence=0.0,
            timestamp=datetime.now().isoformat(),
            metadata={"fallback": True}
        )
        
        return CombinedSearchResult(
            internal_result=fallback_internal,
            external_result=None,
            combined_coverage=0.0,
            recommended_sources=[],
            search_strategy_used="fallback",
            execution_time=0.0
        )
    
    def _create_mock_external_agent(self):
        """Mock 외부 검색 에이전트"""
        class MockExternalAgent:
            def search_external_knowledge(self, query, context):
                from types import SimpleNamespace
                return SimpleNamespace(
                    content=f"Mock 외부 검색 결과: {query}",
                    sources=[{"title": "Mock Source", "url": "http://example.com"}],
                    confidence=0.7,
                    timestamp=datetime.now().isoformat(),
                    token_usage=100
                )
        return MockExternalAgent()
    
    def to_dict(self, combined_result: CombinedSearchResult) -> Dict:
        """CombinedSearchResult를 딕셔너리로 변환"""
        return {
            "internal_result": {
                "content": combined_result.internal_result.content if combined_result.internal_result else "",
                "sources": combined_result.internal_result.sources if combined_result.internal_result else [],
                "coverage_score": combined_result.internal_result.coverage_score if combined_result.internal_result else 0.0,
                "confidence": combined_result.internal_result.confidence if combined_result.internal_result else 0.0
            },
            "external_result": {
                "content": combined_result.external_result.content if combined_result.external_result else "",
                "sources": combined_result.external_result.sources if combined_result.external_result else [],
                "coverage_score": combined_result.external_result.coverage_score if combined_result.external_result else 0.0,
                "confidence": combined_result.external_result.confidence if combined_result.external_result else 0.0
            } if combined_result.external_result else None,
            "combined_coverage": combined_result.combined_coverage,
            "recommended_sources": combined_result.recommended_sources,
            "search_strategy_used": combined_result.search_strategy_used,
            "execution_time": combined_result.execution_time
        }

    def _format_published_date(self, published_date_raw: str) -> str:
        """
        S3 메타데이터의 발행일을 한국어 형식으로 변환
        입력: "2025-07-02T00:00:00.000+09:00"
        출력: "2025년 7월 2일 오전 12시"
        """
        if not published_date_raw:
            return "발행일 미상"
        
        try:
            from datetime import datetime
            import pytz
            
            # ISO 형식 파싱
            dt = datetime.fromisoformat(published_date_raw.replace('Z', '+00:00'))
            
            # 한국 시간대로 변환
            kst = pytz.timezone('Asia/Seoul')
            if dt.tzinfo is None:
                dt = kst.localize(dt)
            else:
                dt = dt.astimezone(kst)
            
            # 한국어 형식으로 변환
            year = dt.year
            month = dt.month
            day = dt.day
            hour = dt.hour
            minute = dt.minute
            
            # 오전/오후 구분
            if hour == 0:
                time_str = "오전 12시"
            elif hour < 12:
                time_str = f"오전 {hour}시"
            elif hour == 12:
                time_str = "오후 12시"
            else:
                time_str = f"오후 {hour-12}시"
            
            # 분 정보 추가 (0분이 아닌 경우)
            if minute > 0:
                time_str += f" {minute}분"
            
            korean_date = f"{year}년 {month}월 {day}일 {time_str}"
            
            logger.info(f"📅 발행일 변환: {published_date_raw} → {korean_date}")
            return korean_date
            
        except Exception as e:
            logger.error(f"발행일 변환 오류: {str(e)} - 원본: {published_date_raw}")
            return f"발행일 파싱 오류 ({published_date_raw[:10]})"

# 사용 예시
if __name__ == "__main__":
    search_agent = SearchAgent()
    
    # 테스트 케이스들
    test_cases = [
        {
            "query": "삼양식품 주가 동향",
            "strategy": "latest_first_search",
            "temporal_info": {
                "has_time_expression": False,
                "search_mode": "latest_first",
                "freshness_priority": 0.8
            }
        },
        {
            "query": "1년 전 삼성전자 실적",
            "strategy": "date_filtered_search", 
            "temporal_info": {
                "has_time_expression": True,
                "search_mode": "date_filtered",
                "calculated_date_range": {
                    "start_date": "2023-01-01T00:00:00+09:00",
                    "end_date": "2023-12-31T23:59:59+09:00"
                }
            }
        },
        {
            "query": "최신 경제 동향",
            "strategy": "multi_source_search",
            "temporal_info": {
                "has_time_expression": False,
                "freshness_priority": 0.9
            }
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"테스트 {i}: {test_case['query']} ({test_case['strategy']})")
        print('='*80)
        
        result = search_agent.search_comprehensive(
            test_case["query"],
            test_case["strategy"],
            test_case.get("temporal_info"),
            {"category": "경제"}
        )
        
        result_dict = search_agent.to_dict(result)
        print(json.dumps(result_dict, ensure_ascii=False, indent=2))
    
    print(f"\n{'='*80}")
    print("SearchAgent 테스트 완료!")
    print('='*80) 
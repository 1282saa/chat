"""
Perplexity API 통합 시스템
- 내부 지식 부족 시 실시간 웹서치
- 쿼리 최적화 및 결과 파싱
- 비용 제어 및 캐싱
- 신뢰성 있는 출처 검증
"""
import json
import os
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import urllib.request
import urllib.parse
import urllib.error
import boto3
import logging
from dataclasses import dataclass

logger = logging.getLogger()
logger.setLevel(logging.INFO)

@dataclass
class SearchResult:
    """검색 결과 데이터 클래스"""
    content: str
    sources: List[Dict]
    query: str
    timestamp: str
    confidence: float
    token_usage: int

class PerplexitySearchAgent:
    """
    Perplexity API를 활용한 지능형 외부 검색 에이전트
    """
    
    def __init__(self):
        self.api_key = os.environ.get("PERPLEXITY_API_KEY")
        self.api_url = "https://api.perplexity.ai/chat/completions"
        
        # DynamoDB 캐싱용 테이블
        self.dynamodb = boto3.client("dynamodb", region_name=os.environ.get("REGION", "ap-northeast-2"))
        self.cache_table = os.environ.get("PERPLEXITY_CACHE_TABLE", "perplexity-search-cache")
        
        # 설정값
        self.config = {
            "model": "sonar-pro",  # 가장 강력한 모델 (실시간 검색 + 인용)
            "max_tokens": 2000,
            "temperature": 0.1,  # 일관성 있는 결과
            "timeout": 30,       # 30초 타임아웃
            "cache_ttl": 3600,   # 1시간 캐시
            "daily_limit": 1000,  # 일일 검색 제한
            "min_confidence": 0.7  # 최소 신뢰도
        }
        
        # 검색 최적화 키워드
        self.search_enhancers = {
            "경제": ["경제", "금융", "증시", "주가", "실적"],
            "기업": ["기업", "회사", "CEO", "사업", "경영"],
            "정치": ["정부", "정책", "법안", "정치", "국회"],
            "기술": ["기술", "IT", "혁신", "개발", "디지털"],
            "시장": ["시장", "산업", "동향", "트렌드", "전망"]
        }
        
    def search_external_knowledge(self, 
                                 query: str, 
                                 context: Dict,
                                 force_search: bool = False) -> SearchResult:
        """
        외부 지식 검색 메인 함수
        """
        try:
            # 1. 검색 필요성 판단
            if not force_search and not self._should_perform_search(context):
                return self._get_skip_result(query, "internal_sufficient")

            # 2. 일일 제한 확인
            if not self._check_daily_limit():
                return self._get_skip_result(query, "daily_limit_exceeded")

            # 3. 캐시 확인
            cached_result = self._get_cached_result(query)
            if cached_result:
                logger.info(f"캐시된 결과 반환: {query}")
                return cached_result

            # 4. 쿼리 최적화
            optimized_query = self._optimize_search_query(query, context)

            # 5. Perplexity API 호출
            raw_result = self._call_perplexity_api(optimized_query)

            # 6. 결과 파싱 및 검증
            parsed_result = self._parse_and_validate_result(raw_result, query)

            # 7. 캐싱
            self._cache_result(query, parsed_result)

            # 8. 사용량 기록
            self._record_usage(parsed_result.token_usage)

            logger.info(f"외부 검색 완료: {query} (신뢰도: {parsed_result.confidence:.2f})")
            return parsed_result

        except Exception as e:
            logger.error(f"외부 검색 오류: {str(e)}")
            return self._get_error_result(query, str(e))
    
    # SmartQueryRouter 호환성을 위한 별칭
    def search_with_caching(self, 
                           query: str, 
                           context: Dict,
                           force_search: bool = False) -> SearchResult:
        """
        search_external_knowledge의 별칭 (SmartQueryRouter 호환성)
        """
        return self.search_external_knowledge(query, context, force_search)
    
    def _should_perform_search(self, context: Dict) -> bool:
        """
        외부 검색 수행 여부 결정
        """
        # 내부 커버리지 확인
        internal_coverage = context.get("internal_coverage", 0.0)
        if internal_coverage >= 0.8:
            return False
        
        # 신선도 요구사항 확인
        freshness_priority = context.get("freshness_priority", 0.0)
        if freshness_priority > 0.7:
            return True
        
        # 복잡도 확인
        complexity_level = context.get("complexity_level", "simple")
        if complexity_level == "complex":
            return True
        
        # 날짜 민감성 확인
        date_strategy = context.get("date_strategy", {})
        if date_strategy.get("priority") == "latest_first":
            return True
        
        return internal_coverage < 0.5
    
    def _optimize_search_query(self, query: str, context: Dict) -> str:
        """
        검색 쿼리 최적화
        """
        # 1. 기본 쿼리 클리닝
        cleaned_query = query.strip()
        
        # 2. 날짜 컨텍스트 추가
        date_info = context.get("date_strategy", {})
        if date_info.get("priority") == "latest_first":
            cleaned_query += " 최신 뉴스"
        elif "2024" in date_info.get("reason", ""):
            cleaned_query += " 2024년"
        
        # 3. 도메인 키워드 강화
        enhanced_query = self._enhance_with_domain_keywords(cleaned_query)
        
        # 4. 검색 지시문 추가
        search_instructions = """
한국의 최신 뉴스와 정보를 중심으로 검색해주세요. 
특히 경제, 기업, 정치 관련 신뢰할 수 있는 출처의 정보를 우선해주세요.
"""
        
        final_query = f"{search_instructions}\n\n질문: {enhanced_query}"
        
        logger.info(f"최적화된 쿼리: {final_query[:100]}...")
        return final_query
    
    def _enhance_with_domain_keywords(self, query: str) -> str:
        """
        도메인별 키워드로 쿼리 강화
        """
        enhanced_query = query
        
        # 기업명이 있으면 관련 키워드 추가
        for domain, keywords in self.search_enhancers.items():
            if any(keyword in query for keyword in keywords):
                if domain == "경제":
                    enhanced_query += " 경제뉴스"
                elif domain == "기업":
                    enhanced_query += " 기업뉴스"
                break
        
        return enhanced_query
    
    def _call_perplexity_api(self, query: str) -> Dict:
        """
        Perplexity API 실제 호출
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.config["model"],
            "messages": [
                {
                    "role": "system",
                    "content": "당신은 한국 뉴스 전문 검색 어시스턴트입니다. 신뢰할 수 있는 출처의 최신 정보를 제공하고, 반드시 출처를 명시해주세요."
                },
                {
                    "role": "user", 
                    "content": query
                }
            ],
            "max_tokens": self.config["max_tokens"],
            "temperature": self.config["temperature"],
            "stream": False,
            "return_citations": True,
            "return_images": False
        }
        
        try:
            # HTTP 요청 생성
            req = urllib.request.Request(
                self.api_url,
                data=json.dumps(payload).encode('utf-8'),
                headers=headers
            )
            
            # API 호출
            start_time = time.time()
            with urllib.request.urlopen(req, timeout=self.config["timeout"]) as response:
                response_data = json.loads(response.read().decode('utf-8'))
            
            elapsed_time = time.time() - start_time
            logger.info(f"Perplexity API 호출 완료: {elapsed_time:.2f}초")
            
            return response_data
            
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else "No error body"
            logger.error(f"Perplexity API HTTP 오류 {e.code}: {error_body}")
            raise Exception(f"API 호출 실패: HTTP {e.code}")
            
        except urllib.error.URLError as e:
            logger.error(f"Perplexity API URL 오류: {str(e)}")
            raise Exception(f"네트워크 오류: {str(e)}")
            
        except Exception as e:
            logger.error(f"Perplexity API 호출 중 예상치 못한 오류: {str(e)}")
            raise
    
    def _parse_and_validate_result(self, raw_result: Dict, original_query: str) -> SearchResult:
        """
        API 결과 파싱 및 검증
        """
        try:
            # 기본 응답 추출
            choices = raw_result.get("choices", [])
            if not choices:
                raise ValueError("응답에 choices가 없음")
            
            message = choices[0].get("message", {})
            content = message.get("content", "")
            
            if not content:
                raise ValueError("응답 내용이 비어있음")
            
            # 사용량 정보
            usage = raw_result.get("usage", {})
            token_usage = usage.get("total_tokens", 0)
            
            # 인용 정보 추출
            citations = raw_result.get("citations", [])
            sources = self._extract_sources(citations)
            
            # 신뢰도 계산
            confidence = self._calculate_confidence(content, sources, token_usage)
            
            # 결과 검증
            if confidence < self.config["min_confidence"]:
                logger.warning(f"낮은 신뢰도 결과: {confidence}")
            
            return SearchResult(
                content=content,
                sources=sources,
                query=original_query,
                timestamp=datetime.now().isoformat(),
                confidence=confidence,
                token_usage=token_usage
            )
            
        except Exception as e:
            logger.error(f"결과 파싱 오류: {str(e)}")
            # Fallback 결과
            return SearchResult(
                content=f"검색 결과 처리 중 오류가 발생했습니다: {str(e)}",
                sources=[],
                query=original_query,
                timestamp=datetime.now().isoformat(),
                confidence=0.0,
                token_usage=0
            )
    
    def _extract_sources(self, citations: List[Dict]) -> List[Dict]:
        """
        인용 정보에서 출처 추출
        """
        sources = []
        
        # citations가 예상과 다른 형태일 수 있으므로 안전하게 처리
        if not isinstance(citations, list):
            logger.warning(f"Citations이 리스트가 아님: {type(citations)}")
            return sources
        
        for i, citation in enumerate(citations[:5], 1):  # 최대 5개 출처
            # citation이 dict가 아닌 경우 안전하게 처리
            if not isinstance(citation, dict):
                logger.warning(f"Citation이 dict가 아님: {type(citation)}")
                continue
                
            source = {
                "index": i,
                "title": citation.get("title", f"출처 {i}"),
                "url": citation.get("url", ""),
                "domain": self._extract_domain(citation.get("url", "")),
                "snippet": citation.get("text", "")[:200] + "..." if len(citation.get("text", "")) > 200 else citation.get("text", "")
            }
            sources.append(source)
        
        return sources
    
    def _extract_domain(self, url: str) -> str:
        """URL에서 도메인 추출"""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.netloc
        except:
            return url
    
    def _calculate_confidence(self, content: str, sources: List[Dict], token_usage: int) -> float:
        """
        검색 결과 신뢰도 계산
        """
        confidence = 0.5  # 기본 점수
        
        # 내용 길이 평가
        if len(content) > 100:
            confidence += 0.1
        if len(content) > 300:
            confidence += 0.1
        
        # 출처 개수 평가
        source_count = len(sources)
        if source_count >= 3:
            confidence += 0.2
        elif source_count >= 1:
            confidence += 0.1
        
        # 신뢰할 수 있는 도메인 확인
        trusted_domains = ["sedaily.com", "yonhapnews.co.kr", "chosun.com", "joongang.co.kr"]
        for source in sources:
            if any(domain in source.get("domain", "") for domain in trusted_domains):
                confidence += 0.1
                break
        
        # 토큰 사용량으로 상세도 평가
        if token_usage > 500:
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _check_daily_limit(self) -> bool:
        """일일 사용 제한 확인"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            response = self.dynamodb.get_item(
                TableName=self.cache_table,
                Key={"query_hash": {"S": f"daily_usage_{today}"}}
            )
            
            if "Item" in response:
                usage_count = int(response["Item"]["usage_count"]["N"])
                return usage_count < self.config["daily_limit"]
            
            return True  # 첫 사용
            
        except Exception as e:
            logger.warning(f"일일 제한 확인 오류: {str(e)}")
            return True  # 오류 시 허용
    
    def _get_cached_result(self, query: str) -> Optional[SearchResult]:
        """캐시된 결과 조회"""
        try:
            query_hash = self._generate_query_hash(query)
            
            response = self.dynamodb.get_item(
                TableName=self.cache_table,
                Key={"query_hash": {"S": query_hash}}
            )
            
            if "Item" in response:
                item = response["Item"]
                
                # TTL 확인
                cache_time = datetime.fromisoformat(item["timestamp"]["S"])
                if datetime.now() - cache_time < timedelta(seconds=self.config["cache_ttl"]):
                    logger.info(f"캐시 히트: {query}")
                    
                    return SearchResult(
                        content=item["content"]["S"],
                        sources=json.loads(item["sources"]["S"]),
                        query=query,
                        timestamp=item["timestamp"]["S"],
                        confidence=float(item["confidence"]["N"]),
                        token_usage=int(item["token_usage"]["N"])
                    )
            
            return None
            
        except Exception as e:
            logger.warning(f"캐시 조회 오류: {str(e)}")
            return None
    
    def _cache_result(self, query: str, result: SearchResult):
        """결과 캐싱"""
        try:
            query_hash = self._generate_query_hash(query)
            
            self.dynamodb.put_item(
                TableName=self.cache_table,
                Item={
                    "query_hash": {"S": query_hash},
                    "content": {"S": result.content},
                    "sources": {"S": json.dumps(result.sources, ensure_ascii=False)},
                    "timestamp": {"S": result.timestamp},
                    "confidence": {"N": str(result.confidence)},
                    "token_usage": {"N": str(result.token_usage)},
                    "ttl": {"N": str(int(time.time()) + self.config["cache_ttl"])}
                }
            )
            
        except Exception as e:
            logger.warning(f"캐싱 오류: {str(e)}")
    
    def _record_usage(self, token_usage: int):
        """사용량 기록"""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            
            # 일일 사용 카운트 증가
            self.dynamodb.update_item(
                TableName=self.cache_table,
                Key={"query_hash": {"S": f"daily_usage_{today}"}},
                UpdateExpression="ADD usage_count :inc SET last_updated = :timestamp",
                ExpressionAttributeValues={
                    ":inc": {"N": "1"},
                    ":timestamp": {"S": datetime.now().isoformat()}
                }
            )
            
        except Exception as e:
            logger.warning(f"사용량 기록 오류: {str(e)}")
    
    def _generate_query_hash(self, query: str) -> str:
        """쿼리 해시 생성"""
        return hashlib.md5(query.encode('utf-8')).hexdigest()
    
    def _get_skip_result(self, query: str, reason: str) -> SearchResult:
        """검색 건너뜀 결과"""
        return SearchResult(
            content=f"외부 검색을 건너뜀: {reason}",
            sources=[],
            query=query,
            timestamp=datetime.now().isoformat(),
            confidence=0.0,
            token_usage=0
        )
    
    def _get_error_result(self, query: str, error: str) -> SearchResult:
        """오류 결과"""
        return SearchResult(
            content=f"외부 검색 중 오류 발생: {error}",
            sources=[],
            query=query,
            timestamp=datetime.now().isoformat(),
            confidence=0.0,
            token_usage=0
        )

# 헬퍼 함수들
def format_search_result_for_display(result: SearchResult) -> Dict:
    """
    검색 결과를 표시용으로 포맷팅
    """
    return {
        "content": result.content,
        "sources": [
            {
                "title": source["title"],
                "url": source["url"],
                "snippet": source["snippet"]
            }
            for source in result.sources
        ],
        "metadata": {
            "timestamp": result.timestamp,
            "confidence": result.confidence,
            "token_usage": result.token_usage
        }
    }

# 사용 예시
if __name__ == "__main__":
    # 테스트용 컨텍스트
    test_context = {
        "internal_coverage": 0.3,  # 낮은 내부 커버리지
        "freshness_priority": 0.8,  # 높은 신선도 요구
        "complexity_level": "moderate",
        "date_strategy": {"priority": "latest_first"}
    }
    
    agent = PerplexitySearchAgent()
    
    # 테스트 검색
    test_queries = [
        "삼양식품 최신 주가 동향",
        "2024년 한국 경제 전망",
        "최근 반도체 시장 이슈"
    ]
    
    for query in test_queries:
        print(f"\n=== 테스트 검색: {query} ===")
        result = agent.search_external_knowledge(query, test_context)
        formatted = format_search_result_for_display(result)
        print(json.dumps(formatted, ensure_ascii=False, indent=2)) 
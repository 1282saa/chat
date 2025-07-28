"""
날짜 지능형 처리 시스템 (Date Intelligence Processor)
- S3 메타데이터 발행일 형식 처리 (2025-07-02T00:00:00.000+09:00)
- 자연어 날짜 표현 파싱 및 변환
- 최신순 우선 검색 로직
- 날짜 범위 계산 및 필터링
"""
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional, Union
import pytz
from dateutil import parser
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DateIntelligenceProcessor:
    """
    뉴스 서비스를 위한 고급 날짜 처리 엔진
    """
    
    def __init__(self):
        # 한국 시간대 설정
        self.kst = pytz.timezone('Asia/Seoul')
        self.current_time_kst = datetime.now(self.kst)
        
        # S3 메타데이터 날짜 형식
        self.s3_date_format = "%Y-%m-%dT%H:%M:%S.%f%z"  # 2025-07-02T00:00:00.000+09:00
        
        # 날짜 표현 패턴 (확장된 버전)
        self.patterns = {
            # 상대적 시간 표현
            "relative_time": {
                r'오늘': (0, 'days'),
                r'어제': (-1, 'days'),
                r'그제|그저께': (-2, 'days'),
                r'모레': (2, 'days'),
                r'내일': (1, 'days'),
                r'이번\s*주': (0, 'weeks'),
                r'지난\s*주|저번\s*주': (-1, 'weeks'),
                r'다음\s*주': (1, 'weeks'),
                r'이번\s*달|이번\s*월': (0, 'months'),
                r'지난\s*달|저번\s*달|지난\s*월': (-1, 'months'),
                r'다음\s*달|다음\s*월': (1, 'months'),
                r'올해|금년': (0, 'years'),
                r'작년|지난해': (-1, 'years'),
                r'내년|내해': (1, 'years')
            },
            
            # 구체적 기간 표현 (N 단위 전/후)
            "specific_period": {
                r'(\d+)년\s*전': ('years', -1),
                r'(\d+)년\s*후': ('years', 1),
                r'(\d+)(달|개월)\s*전': ('months', -1),
                r'(\d+)(달|개월)\s*후': ('months', 1),
                r'(\d+)주\s*전': ('weeks', -1),
                r'(\d+)주\s*후': ('weeks', 1),
                r'(\d+)일\s*전': ('days', -1),
                r'(\d+)일\s*후': ('days', 1),
                r'(\d+)시간\s*전': ('hours', -1),
                r'(\d+)시간\s*후': ('hours', 1)
            },
            
            # 절대 날짜 표현
            "absolute_date": [
                r'(\d{4})년',
                r'(\d{4})-(\d{1,2})-(\d{1,2})',
                r'(\d{1,2})월\s*(\d{1,2})일',
                r'(\d{4})년\s*(\d{1,2})월',
                r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일'
            ],
            
            # 계절 및 분기
            "seasons": {
                r'봄': (3,4,5),      # 3월-5월
                r'여름': (6,7,8),    # 6월-8월
                r'가을': (9,10,11),   # 9월-11월
                r'겨울': (12,1,2),   # 12월-2월
                r'상반기': (1,2,3,4,5,6),  # 1월-6월
                r'하반기': (7,8,9,10,11,12), # 7월-12월
                r'1분기': (1,2,3),   # 1월-3월
                r'2분기': (4,5,6),   # 4월-6월
                r'3분기': (7,8,9),   # 7월-9월
                r'4분기': (10,11,12)  # 10월-12월
            },
            
            # 신선도 키워드
            "freshness": [
                r'최근', r'최신', r'요즘', r'현재', r'지금',
                r'실시간', r'라이브', r'속보'
            ]
        }
    
    def analyze_query_temporal_expressions(self, query: str) -> Dict:
        """
        질문에서 시간 표현을 종합적으로 분석
        """
        analysis_result = {
            "query": query,
            "current_time_kst": self.current_time_kst.isoformat(),
            "detected_expressions": {},
            "calculated_ranges": [],
            "primary_strategy": "latest_first",  # 기본값
            "confidence_score": 0.0,
            "s3_filter_params": {}
        }
        
        try:
            # 1. 상대적 시간 표현 감지
            relative_results = self._detect_relative_time(query)
            if relative_results:
                analysis_result["detected_expressions"]["relative"] = relative_results
                analysis_result["calculated_ranges"].extend(
                    self._calculate_relative_ranges(relative_results)
                )
            
            # 2. 구체적 기간 표현 감지
            specific_results = self._detect_specific_period(query)
            if specific_results:
                analysis_result["detected_expressions"]["specific"] = specific_results
                analysis_result["calculated_ranges"].extend(
                    self._calculate_specific_ranges(specific_results)
                )
            
            # 3. 절대 날짜 표현 감지
            absolute_results = self._detect_absolute_date(query)
            if absolute_results:
                analysis_result["detected_expressions"]["absolute"] = absolute_results
                analysis_result["calculated_ranges"].extend(
                    self._calculate_absolute_ranges(absolute_results)
                )
            
            # 4. 계절/분기 표현 감지
            season_results = self._detect_seasons(query)
            if season_results:
                analysis_result["detected_expressions"]["seasons"] = season_results
                analysis_result["calculated_ranges"].extend(
                    self._calculate_season_ranges(season_results)
                )
            
            # 5. 신선도 키워드 감지
            freshness_score = self._calculate_freshness_priority(query)
            analysis_result["freshness_priority"] = freshness_score
            
            # 6. 최종 전략 결정
            final_strategy = self._determine_search_strategy(analysis_result)
            analysis_result.update(final_strategy)
            
            # 7. S3 필터 파라미터 생성
            s3_params = self._generate_s3_filter_params(analysis_result)
            analysis_result["s3_filter_params"] = s3_params
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"날짜 분석 중 오류: {str(e)}")
            return self._get_fallback_analysis(query)
    
    def _detect_relative_time(self, query: str) -> List[Dict]:
        """상대적 시간 표현 감지"""
        results = []
        
        for pattern, (offset, unit) in self.patterns["relative_time"].items():
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                results.append({
                    "expression": match.group(),
                    "type": "relative",
                    "offset": offset,
                    "unit": unit,
                    "position": match.span()
                })
        
        return results
    
    def _detect_specific_period(self, query: str) -> List[Dict]:
        """구체적 기간 표현 감지 (N일 전, N년 전 등)"""
        results = []
        
        for pattern, (unit, direction) in self.patterns["specific_period"].items():
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                try:
                    # 숫자 추출
                    number = int(match.group(1))
                    results.append({
                        "expression": match.group(),
                        "type": "specific_period", 
                        "number": number,
                        "unit": unit,
                        "direction": direction,
                        "position": match.span()
                    })
                except (ValueError, IndexError):
                    continue
        
        return results
    
    def _detect_absolute_date(self, query: str) -> List[Dict]:
        """절대 날짜 표현 감지"""
        results = []
        
        for pattern in self.patterns["absolute_date"]:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                results.append({
                    "expression": match.group(),
                    "type": "absolute_date",
                    "groups": match.groups(),
                    "position": match.span()
                })
        
        return results
    
    def _detect_seasons(self, query: str) -> List[Dict]:
        """계절 및 분기 표현 감지"""
        results = []
        
        for pattern, months in self.patterns["seasons"].items():
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                # months는 tuple로, 시작월과 끝월을 계산
                start_month = min(months)
                end_month = max(months)
                results.append({
                    "expression": match.group(),
                    "type": "season",
                    "start_month": start_month,
                    "end_month": end_month,
                    "all_months": months,
                    "position": match.span()
                })
        
        return results
    
    def _calculate_relative_ranges(self, relative_results: List[Dict]) -> List[Dict]:
        """상대적 시간 표현을 날짜 범위로 변환"""
        ranges = []
        
        for result in relative_results:
            try:
                current = self.current_time_kst
                offset = result["offset"]
                unit = result["unit"]
                
                if unit == "days":
                    target_date = current + timedelta(days=offset)
                    ranges.append({
                        "start_date": target_date.replace(hour=0, minute=0, second=0, microsecond=0),
                        "end_date": target_date.replace(hour=23, minute=59, second=59, microsecond=999999),
                        "type": "single_day",
                        "source": result["expression"]
                    })
                
                elif unit == "weeks":
                    # 주의 시작(월요일)과 끝(일요일) 계산
                    days_since_monday = current.weekday()
                    week_start = current - timedelta(days=days_since_monday) + timedelta(weeks=offset)
                    week_end = week_start + timedelta(days=6)
                    
                    ranges.append({
                        "start_date": week_start.replace(hour=0, minute=0, second=0, microsecond=0),
                        "end_date": week_end.replace(hour=23, minute=59, second=59, microsecond=999999),
                        "type": "week_range",
                        "source": result["expression"]
                    })
                
                elif unit == "months":
                    if offset == 0:  # 이번 달
                        month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                        if current.month == 12:
                            month_end = current.replace(year=current.year+1, month=1, day=1) - timedelta(microseconds=1)
                        else:
                            month_end = current.replace(month=current.month+1, day=1) - timedelta(microseconds=1)
                    else:
                        # 다른 달 계산 (복잡하므로 근사치 사용)
                        target_date = current + timedelta(days=30*offset)
                        month_start = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                        month_end = target_date.replace(day=28, hour=23, minute=59, second=59, microsecond=999999)
                    
                    ranges.append({
                        "start_date": month_start,
                        "end_date": month_end,
                        "type": "month_range",
                        "source": result["expression"]
                    })
                
                elif unit == "years":
                    target_year = current.year + offset
                    year_start = current.replace(year=target_year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
                    year_end = current.replace(year=target_year, month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
                    
                    ranges.append({
                        "start_date": year_start,
                        "end_date": year_end,
                        "type": "year_range",
                        "source": result["expression"]
                    })
                    
            except Exception as e:
                logger.warning(f"상대 시간 계산 오류: {str(e)}")
                continue
        
        return ranges
    
    def _calculate_specific_ranges(self, specific_results: List[Dict]) -> List[Dict]:
        """구체적 기간 표현을 날짜 범위로 변환"""
        ranges = []
        
        for result in specific_results:
            try:
                current = self.current_time_kst
                number = result["number"]
                unit = result["unit"]
                direction = result["direction"]
                
                if unit == "days":
                    target_date = current + timedelta(days=number * direction)
                    # 하루 범위
                    ranges.append({
                        "start_date": target_date.replace(hour=0, minute=0, second=0, microsecond=0),
                        "end_date": target_date.replace(hour=23, minute=59, second=59, microsecond=999999),
                        "type": "specific_day",
                        "source": result["expression"]
                    })
                
                elif unit == "weeks":
                    target_date = current + timedelta(weeks=number * direction)
                    # 해당 주 범위
                    days_since_monday = target_date.weekday()
                    week_start = target_date - timedelta(days=days_since_monday)
                    week_end = week_start + timedelta(days=6)
                    
                    ranges.append({
                        "start_date": week_start.replace(hour=0, minute=0, second=0, microsecond=0),
                        "end_date": week_end.replace(hour=23, minute=59, second=59, microsecond=999999),
                        "type": "specific_week",
                        "source": result["expression"]
                    })
                
                elif unit == "months":
                    # 근사치 계산 (30일 기준)
                    target_date = current + timedelta(days=30 * number * direction)
                    month_start = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                    
                    ranges.append({
                        "start_date": month_start,
                        "end_date": target_date.replace(day=28, hour=23, minute=59, second=59, microsecond=999999),
                        "type": "specific_month",
                        "source": result["expression"]
                    })
                
                elif unit == "years":
                    target_year = current.year + (number * direction)
                    year_start = datetime(target_year, 1, 1, tzinfo=self.kst)
                    year_end = datetime(target_year, 12, 31, 23, 59, 59, 999999, tzinfo=self.kst)
                    
                    ranges.append({
                        "start_date": year_start,
                        "end_date": year_end,
                        "type": "specific_year",
                        "source": result["expression"]
                    })
                
                elif unit == "hours":
                    target_time = current + timedelta(hours=number * direction)
                    # 1시간 범위
                    ranges.append({
                        "start_date": target_time.replace(minute=0, second=0, microsecond=0),
                        "end_date": target_time.replace(minute=59, second=59, microsecond=999999),
                        "type": "specific_hour",
                        "source": result["expression"]
                    })
                    
            except Exception as e:
                logger.warning(f"구체적 기간 계산 오류: {str(e)}")
                continue
        
        return ranges
    
    def _calculate_absolute_ranges(self, absolute_results: List[Dict]) -> List[Dict]:
        """절대 날짜 표현을 날짜 범위로 변환"""
        ranges = []
        
        for result in absolute_results:
            try:
                groups = result["groups"]
                
                # 연도만 있는 경우 (2024년)
                if len(groups) == 1 and len(groups[0]) == 4:
                    year = int(groups[0])
                    start_date = datetime(year, 1, 1, tzinfo=self.kst)
                    end_date = datetime(year, 12, 31, 23, 59, 59, 999999, tzinfo=self.kst)
                    
                    ranges.append({
                        "start_date": start_date,
                        "end_date": end_date,
                        "type": "absolute_year",
                        "source": result["expression"]
                    })
                
                # 년-월-일 형식 (2024-01-15)
                elif len(groups) == 3:
                    year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                    target_date = datetime(year, month, day, tzinfo=self.kst)
                    
                    ranges.append({
                        "start_date": target_date.replace(hour=0, minute=0, second=0, microsecond=0),
                        "end_date": target_date.replace(hour=23, minute=59, second=59, microsecond=999999),
                        "type": "absolute_date",
                        "source": result["expression"]
                    })
                
                # 월-일 형식 (1월 15일) - 현재 연도 가정
                elif len(groups) == 2:
                    month, day = int(groups[0]), int(groups[1])
                    current_year = self.current_time_kst.year
                    target_date = datetime(current_year, month, day, tzinfo=self.kst)
                    
                    ranges.append({
                        "start_date": target_date.replace(hour=0, minute=0, second=0, microsecond=0),
                        "end_date": target_date.replace(hour=23, minute=59, second=59, microsecond=999999),
                        "type": "absolute_month_day",
                        "source": result["expression"]
                    })
                    
            except Exception as e:
                logger.warning(f"절대 날짜 계산 오류: {str(e)}")
                continue
        
        return ranges
    
    def _calculate_season_ranges(self, season_results: List[Dict]) -> List[Dict]:
        """계절/분기 표현을 날짜 범위로 변환"""
        ranges = []
        
        for result in season_results:
            try:
                start_month = result["start_month"]
                end_month = result["end_month"]
                current_year = self.current_time_kst.year
                
                # 겨울의 경우 연도를 넘나들 수 있음
                if start_month > end_month:  # 겨울 (12월-2월)
                    # 이번 겨울 vs 지난 겨울 판단
                    if self.current_time_kst.month >= start_month:  # 12월
                        start_date = datetime(current_year, start_month, 1, tzinfo=self.kst)
                        end_date = datetime(current_year + 1, end_month, 28, 23, 59, 59, 999999, tzinfo=self.kst)
                    else:  # 1-2월
                        start_date = datetime(current_year - 1, start_month, 1, tzinfo=self.kst)
                        end_date = datetime(current_year, end_month, 28, 23, 59, 59, 999999, tzinfo=self.kst)
                else:
                    start_date = datetime(current_year, start_month, 1, tzinfo=self.kst)
                    # 마지막 날 계산
                    if end_month == 12:
                        end_date = datetime(current_year, end_month, 31, 23, 59, 59, 999999, tzinfo=self.kst)
                    else:
                        end_date = datetime(current_year, end_month + 1, 1, tzinfo=self.kst) - timedelta(microseconds=1)
                
                ranges.append({
                    "start_date": start_date,
                    "end_date": end_date,
                    "type": "season_range",
                    "source": result["expression"]
                })
                
            except Exception as e:
                logger.warning(f"계절 날짜 계산 오류: {str(e)}")
                continue
        
        return ranges
    
    def _calculate_freshness_priority(self, query: str) -> float:
        """신선도 우선순위 계산 (0.0-1.0)"""
        freshness_score = 0.0
        
        for pattern in self.patterns["freshness"]:
            if re.search(pattern, query, re.IGNORECASE):
                freshness_score += 0.2
        
        # 특별한 키워드는 더 높은 점수
        if re.search(r'실시간|속보|긴급', query, re.IGNORECASE):
            freshness_score += 0.4
        
        return min(freshness_score, 1.0)
    
    def _determine_search_strategy(self, analysis_result: Dict) -> Dict:
        """최종 검색 전략 결정"""
        
        # 날짜 표현이 있는지 확인
        has_date_expressions = bool(analysis_result["detected_expressions"])
        
        if not has_date_expressions:
            # 날짜 표현이 없으면 최신순 우선
            return {
                "primary_strategy": "latest_first",
                "date_range": {
                    "start_date": (self.current_time_kst - timedelta(days=30)).isoformat(),
                    "end_date": self.current_time_kst.isoformat(),
                    "priority": "latest_first",
                    "reason": "no_date_expression_default_to_recent"
                },
                "confidence_score": 0.9,
                "search_mode": "recency_optimized"
            }
        
        # 날짜 표현이 있으면 가장 구체적인 범위 선택
        if analysis_result["calculated_ranges"]:
            primary_range = analysis_result["calculated_ranges"][0]  # 첫 번째 범위 사용
            
            return {
                "primary_strategy": "date_filtered",
                "date_range": {
                    "start_date": primary_range["start_date"].isoformat(),
                    "end_date": primary_range["end_date"].isoformat(),
                    "priority": "date_specific",
                    "reason": f"detected_expression: {primary_range['source']}"
                },
                "confidence_score": 0.85,
                "search_mode": "date_filtered"
            }
        
        # Fallback
        return {
            "primary_strategy": "latest_first",
            "date_range": {
                "start_date": (self.current_time_kst - timedelta(days=7)).isoformat(),
                "end_date": self.current_time_kst.isoformat(),
                "priority": "latest_first",
                "reason": "fallback_recent"
            },
            "confidence_score": 0.6,
            "search_mode": "fallback"
        }
    
    def _generate_s3_filter_params(self, analysis_result: Dict) -> Dict:
        """
        S3 메타데이터 필터링을 위한 파라미터 생성
        S3 형식: 2025-07-02T00:00:00.000+09:00
        """
        date_range = analysis_result.get("date_range", {})
        
        try:
            # ISO 문자열을 datetime 객체로 변환
            start_date = parser.isoparse(date_range["start_date"])
            end_date = parser.isoparse(date_range["end_date"])
            
            # S3 메타데이터 형식으로 변환
            s3_start = start_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + start_date.strftime("%z")
            s3_end = end_date.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + end_date.strftime("%z")
            
            return {
                "published_date_filter": {
                    "start": s3_start,
                    "end": s3_end,
                    "format": "ISO_8601_KST"
                },
                "sort_order": "desc" if analysis_result["primary_strategy"] == "latest_first" else "asc",
                "max_results": 50,
                "boost_recent": analysis_result.get("freshness_priority", 0.0) > 0.7
            }
            
        except Exception as e:
            logger.error(f"S3 필터 파라미터 생성 오류: {str(e)}")
            return {
                "published_date_filter": None,
                "sort_order": "desc",
                "max_results": 20,
                "boost_recent": True
            }
    
    def convert_s3_date_to_readable(self, s3_date_str: str) -> str:
        """
        S3 메타데이터 날짜를 읽기 쉬운 형식으로 변환
        """
        try:
            dt = datetime.strptime(s3_date_str, self.s3_date_format)
            kst_dt = dt.astimezone(self.kst)
            return kst_dt.strftime("%Y년 %m월 %d일 %H시 %M분")
        except Exception as e:
            logger.warning(f"날짜 변환 오류: {str(e)}")
            return s3_date_str
    
    def _get_fallback_analysis(self, query: str) -> Dict:
        """Fallback 분석 결과"""
        return {
            "query": query,
            "current_time_kst": self.current_time_kst.isoformat(),
            "detected_expressions": {},
            "calculated_ranges": [],
            "primary_strategy": "latest_first",
            "date_range": {
                "start_date": (self.current_time_kst - timedelta(days=30)).isoformat(),
                "end_date": self.current_time_kst.isoformat(),
                "priority": "latest_first",
                "reason": "fallback_analysis"
            },
            "confidence_score": 0.5,
            "s3_filter_params": {
                "sort_order": "desc",
                "max_results": 20,
                "boost_recent": True
            },
            "fallback": True
        }

# 사용 예시 및 테스트
if __name__ == "__main__":
    processor = DateIntelligenceProcessor()
    
    # 테스트 케이스들
    test_queries = [
        "삼양식품 주가는 어떤가요?",           # 날짜 표현 없음 → 최신순
        "1년 전 삼양식품은 어땠나요?",         # 구체적 기간
        "어제 주요 뉴스는?",                  # 상대적 시간
        "2024년 삼성전자 실적",              # 절대 날짜
        "올해 상반기 경제 동향",              # 계절/분기
        "최근 부동산 시장 동향"               # 신선도 키워드
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n=== 테스트 {i}: {query} ===")
        result = processor.analyze_query_temporal_expressions(query)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str)) 
#!/usr/bin/env python3
"""
날짜 컨텍스트 관리자
- 모든 AI 처리 과정에서 공통으로 사용할 날짜 정보 제공
- 사용자 질문 처리 시작 시점에 현재 날짜 컨텍스트 생성
"""

from datetime import datetime, timedelta
import pytz
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class DateContextManager:
    """
    전체 AI 처리 과정에서 사용할 날짜 컨텍스트 관리
    """
    
    def __init__(self):
        # 한국 시간대
        self.kst = pytz.timezone('Asia/Seoul')
        self.current_time = datetime.now(self.kst)
        
        # 날짜 컨텍스트 생성
        self.date_context = self._create_date_context()
        
        logger.info(f"📅 날짜 컨텍스트 생성됨: {self.current_time.strftime('%Y년 %m월 %d일 %H시 %M분')}")
    
    def _create_date_context(self) -> Dict[str, Any]:
        """
        포괄적인 날짜 컨텍스트 생성
        모든 AI 에이전트가 공유할 날짜 정보
        """
        current = self.current_time
        
        # 요일 한글 변환
        weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        
        context = {
            # 기본 현재 정보
            "현재_시간": current,
            "현재_날짜_문자열": current.strftime('%Y년 %m월 %d일'),
            "현재_요일": weekdays[current.weekday()],
            "현재_년도": current.year,
            "현재_월": current.month,
            "현재_일": current.day,
            "현재_시": current.hour,
            "현재_분": current.minute,
            
            # 상대적 날짜들
            "어제": current - timedelta(days=1),
            "내일": current + timedelta(days=1),
            "일주일_전": current - timedelta(days=7),
            "일주일_후": current + timedelta(days=7),
            "한달_전": current - timedelta(days=30),
            "한달_후": current + timedelta(days=30),
            "작년": current.replace(year=current.year-1),
            "내년": current.replace(year=current.year+1),
            
            # 연도별 계산
            "1년_전_년도": current.year - 1,
            "2년_전_년도": current.year - 2,
            "3년_전_년도": current.year - 3,
            "5년_전_년도": current.year - 5,
            "10년_전_년도": current.year - 10,
            
            # AI용 프롬프트 문자열
            "ai_date_prompt": self._generate_ai_date_prompt(),
            
            # 검색용 ISO 형식
            "오늘_시작": current.replace(hour=0, minute=0, second=0).isoformat(),
            "오늘_끝": current.replace(hour=23, minute=59, second=59).isoformat(),
            "어제_시작": (current - timedelta(days=1)).replace(hour=0, minute=0, second=0).isoformat(),
            "어제_끝": (current - timedelta(days=1)).replace(hour=23, minute=59, second=59).isoformat(),
            
            # 메타 정보
            "생성_시각": current.isoformat(),
            "timezone": "Asia/Seoul"
        }
        
        return context
    
    def _generate_ai_date_prompt(self) -> str:
        """
        AI 에이전트들이 사용할 날짜 정보 프롬프트 생성
        """
        current = self.current_time
        weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
        
        prompt = f"""
## 📅 현재 날짜 및 시간 정보 (한국 표준시)

**현재 시점:**
- 오늘: {current.strftime('%Y년 %m월 %d일')} ({weekdays[current.weekday()]})
- 현재 시각: {current.strftime('%H시 %M분')}
- 현재 년도: {current.year}년

**상대적 날짜 참조:**
- 어제: {current.year}년 {current.month}월 {current.day-1}일
- 작년/지난해: {current.year-1}년
- 1년 전: {current.year-1}년
- 2년 전: {current.year-2}년
- 3년 전: {current.year-3}년

⚠️ **중요**: 위 정보를 기준으로 모든 날짜 관련 질문과 계산을 수행하세요.
날짜를 추측하지 말고 반드시 위 정보를 참조하세요.
"""
        return prompt.strip()
    
    def get_date_context(self) -> Dict[str, Any]:
        """날짜 컨텍스트 반환"""
        return self.date_context
    
    def get_ai_prompt(self) -> str:
        """AI 에이전트용 날짜 프롬프트 반환"""
        return self.date_context["ai_date_prompt"]
    
    def calculate_relative_date(self, expression: str) -> Dict[str, Any]:
        """
        상대적 날짜 표현을 실제 날짜로 계산
        
        Args:
            expression: "1년 전", "어제", "작년" 등
            
        Returns:
            계산된 날짜 정보
        """
        try:
            current = self.current_time
            
            # 상대적 표현 매핑
            relative_mappings = {
                "오늘": timedelta(days=0),
                "어제": timedelta(days=-1),
                "내일": timedelta(days=1),
                "일주일 전": timedelta(days=-7),
                "일주일 후": timedelta(days=7),
                "한달 전": timedelta(days=-30),
                "한달 후": timedelta(days=30),
                "작년": timedelta(days=-365),
                "지난해": timedelta(days=-365),
                "내년": timedelta(days=365),
            }
            
            # 숫자 + 단위 패턴 처리
            import re
            
            # "N년 전" 패턴
            year_pattern = re.search(r'(\d+)년\s*전', expression)
            if year_pattern:
                years = int(year_pattern.group(1))
                target_date = current.replace(year=current.year - years)
                return {
                    "target_date": target_date,
                    "year": target_date.year,
                    "date_string": target_date.strftime('%Y년 %m월 %d일'),
                    "iso_string": target_date.isoformat(),
                    "expression": expression
                }
            
            # "N개월 전" 패턴
            month_pattern = re.search(r'(\d+)개?월\s*전', expression)
            if month_pattern:
                months = int(month_pattern.group(1))
                target_date = current - timedelta(days=months * 30)
                return {
                    "target_date": target_date,
                    "year": target_date.year,
                    "date_string": target_date.strftime('%Y년 %m월 %d일'),
                    "iso_string": target_date.isoformat(),
                    "expression": expression
                }
            
            # "N일 전" 패턴
            day_pattern = re.search(r'(\d+)일\s*전', expression)
            if day_pattern:
                days = int(day_pattern.group(1))
                target_date = current - timedelta(days=days)
                return {
                    "target_date": target_date,
                    "year": target_date.year,
                    "date_string": target_date.strftime('%Y년 %m월 %d일'),
                    "iso_string": target_date.isoformat(),
                    "expression": expression
                }
            
            # 직접 매핑된 표현들
            if expression in relative_mappings:
                target_date = current + relative_mappings[expression]
                return {
                    "target_date": target_date,
                    "year": target_date.year,
                    "date_string": target_date.strftime('%Y년 %m월 %d일'),
                    "iso_string": target_date.isoformat(),
                    "expression": expression
                }
            
            # 매칭되지 않는 경우 현재 날짜 반환
            logger.warning(f"인식되지 않은 날짜 표현: {expression}")
            return {
                "target_date": current,
                "year": current.year,
                "date_string": current.strftime('%Y년 %m월 %d일'),
                "iso_string": current.isoformat(),
                "expression": expression,
                "warning": "인식되지 않은 표현"
            }
            
        except Exception as e:
            logger.error(f"날짜 계산 오류: {str(e)}")
            return {
                "target_date": self.current_time,
                "year": self.current_time.year,
                "date_string": self.current_time.strftime('%Y년 %m월 %d일'),
                "iso_string": self.current_time.isoformat(),
                "expression": expression,
                "error": str(e)
            }
    
    def is_date_related_query(self, query: str) -> bool:
        """
        질문이 날짜 관련인지 판단
        """
        date_keywords = [
            "년", "월", "일", "어제", "오늘", "내일", 
            "작년", "내년", "지난해", "올해", "최근", 
            "전", "후", "시간", "때", "시점", "기간"
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in date_keywords)
    
    def refresh_context(self):
        """
        날짜 컨텍스트 새로고침 (장시간 실행 시 사용)
        """
        self.current_time = datetime.now(self.kst)
        self.date_context = self._create_date_context()
        logger.info(f"📅 날짜 컨텍스트 새로고침: {self.current_time.strftime('%Y년 %m월 %d일 %H시 %M분')}")

# 글로벌 인스턴스 (싱글톤 패턴)
_date_context_manager = None

def get_date_context_manager() -> DateContextManager:
    """
    글로벌 DateContextManager 인스턴스 반환
    """
    global _date_context_manager
    if _date_context_manager is None:
        _date_context_manager = DateContextManager()
    return _date_context_manager 
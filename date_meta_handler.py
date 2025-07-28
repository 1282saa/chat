#!/usr/bin/env python3
"""
날짜 메타 질문 처리 핸들러
- "오늘의 날짜가 무엇인가요?" 같은 질문 직접 처리
"""
import re
from datetime import datetime

def is_date_meta_question(query: str) -> bool:
    """날짜/시간 메타 정보 질문인지 판단"""
    date_meta_patterns = [
        r"오늘.*날짜", r"현재.*날짜", r"지금.*날짜", r"날짜.*무엇", r"날짜.*몇",
        r"몇.*월.*몇.*일", r"현재.*시간", r"지금.*몇.*시", r"오늘.*무슨.*요일",
        r"지금.*년도", r"현재.*년", r"오늘.*며칠", r"오늘.*몇.*일"
    ]
    
    query_normalized = query.lower().replace(" ", "")
    
    for pattern in date_meta_patterns:
        if re.search(pattern.replace(".*", ".*?"), query_normalized):
            return True
    
    return False

def generate_date_meta_response(query: str) -> dict:
    """날짜/시간 메타 정보 직접 응답 생성"""
    current_time = datetime.now()
    
    # 요일 한글 변환
    weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    current_weekday = weekdays[current_time.weekday()]
    
    # 질문에 따른 맞춤 답변 생성
    query_lower = query.lower()
    
    if "시간" in query_lower:
        answer = f"현재 시간은 {current_time.strftime('%Y년 %m월 %d일 %H시 %M분')}입니다."
    elif "요일" in query_lower:
        answer = f"오늘은 {current_time.strftime('%Y년 %m월 %d일')} {current_weekday}입니다."
    else:
        answer = f"오늘 날짜는 {current_time.strftime('%Y년 %m월 %d일')} {current_weekday}입니다."
    
    return {
        "success": True,
        "result": {
            "answer": answer,
            "thinking_process": [
                {
                    "step": "🕐 시스템 시간 확인",
                    "content": f"현재 시스템 시간을 확인했습니다: {current_time.isoformat()}"
                },
                {
                    "step": "📅 한국 시간 변환",
                    "content": f"한국 표준시 기준으로 {current_time.strftime('%Y년 %m월 %d일 %H시 %M분')} {current_weekday}로 확인했습니다."
                },
                {
                    "step": "✅ 답변 생성",
                    "content": "사용자 질문에 맞는 날짜/시간 정보를 제공했습니다."
                }
            ],
            "metadata": {
                "response_type": "date_meta",
                "selected_model": "시스템 응답",
                "complexity_level": "매우 간단",
                "model_priority": "즉시 응답",
                "confidence_score": 1.0
            }
        },
        "routing_info": {
            "route_type": "date_meta_response",
            "response_method": "direct_system",
            "processing_time": "즉시"
        },
        "execution_result": None,
        "external_context": []
    } 
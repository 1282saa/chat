#!/usr/bin/env python3
"""
Lambda 환경 테스트 스크립트
"""
import sys
import os
import json
import traceback

def test_imports():
    """Import 테스트"""
    print("=== Import 테스트 시작 ===")
    
    # 기본 모듈들
    try:
        import boto3
        print("✅ boto3 import 성공")
    except Exception as e:
        print(f"❌ boto3 import 실패: {e}")
    
    # Lambda Layer 경로 추가
    sys.path.append('/opt/python')
    sys.path.append('.')
    
    print(f"Python Path: {sys.path}")
    
    # Lambda Layer 디렉토리 확인
    try:
        layer_path = '/opt/python'
        if os.path.exists(layer_path):
            contents = os.listdir(layer_path)
            print(f"✅ Lambda Layer 내용: {contents}")
        else:
            print("❌ Lambda Layer 경로 없음")
    except Exception as e:
        print(f"❌ Lambda Layer 확인 실패: {e}")
    
    # SmartQueryRouter import 테스트
    try:
        from smart_router.query_router import SmartQueryRouter
        print("✅ SmartQueryRouter import 성공")
        
        # 간단한 인스턴스 생성 테스트
        router = SmartQueryRouter()
        print("✅ SmartQueryRouter 인스턴스 생성 성공")
        
    except Exception as e:
        print(f"❌ SmartQueryRouter import/인스턴스 생성 실패: {e}")
        print(f"❌ 상세 오류: {traceback.format_exc()}")
    
    # Enhanced Agent System 테스트
    try:
        from workflow_engine.conditional_execution import ConditionalExecutionEngine
        print("✅ ConditionalExecutionEngine import 성공")
    except Exception as e:
        print(f"❌ ConditionalExecutionEngine import 실패: {e}")
    
    print("=== Import 테스트 완료 ===")

def test_handler_simplified():
    """단순화된 핸들러 테스트"""
    print("=== 단순화된 핸들러 테스트 시작 ===")
    
    test_event = {
        "httpMethod": "POST",
        "pathParameters": {"projectId": "test-project"},
        "body": json.dumps({
            "userInput": "테스트 질문",
            "chat_history": [],
            "useKnowledgeBase": True,
            "modelId": "apac.anthropic.claude-3-haiku-20240307-v1:0"
        })
    }
    
    try:
        # generate.py의 handler 함수 호출
        sys.path.append('/var/task')
        import generate
        
        result = generate.handler(test_event, {})
        print(f"✅ Handler 테스트 성공: {result['statusCode']}")
        
        if result['statusCode'] != 200:
            print(f"❌ Handler 응답 오류: {result}")
        
    except Exception as e:
        print(f"❌ Handler 테스트 실패: {e}")
        print(f"❌ 상세 오류: {traceback.format_exc()}")
    
    print("=== 단순화된 핸들러 테스트 완료 ===")

if __name__ == "__main__":
    print("🧪 Lambda 환경 테스트 시작")
    test_imports()
    test_handler_simplified()
    print("�� Lambda 환경 테스트 완료") 
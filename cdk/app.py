#!/usr/bin/env python3
import aws_cdk as cdk
import os
from bedrock_stack import ChatbotStack
from frontend_stack import NewsSummarizerFrontendStack
from conversation_stack import ChatbotConversationStack
# from performance_optimization_stack import PerformanceOptimizationStack
# from cicd_stack import CICDStack

app = cdk.App()

# 환경 설정
env = cdk.Environment(
    account=app.node.try_get_context("account"),
    region=app.node.try_get_context("region") or "ap-northeast-2"
)

# 🔧 환경별 배포 설정
# GitHub Actions에서 STACK_SUFFIX를 통해 환경 구분
environments = ['', 'Prod', 'Dev']  # 기본(로컬), 프로덕션, 개발

for suffix in environments:
    if suffix == '':
        # 로컬 개발용 (기본)
        stack_suffix = ''
        domain_suffix = 'local'
        print("🏠 Creating LOCAL development stacks")
    elif suffix == 'Prod':
        # 프로덕션 환경
        stack_suffix = suffix
        domain_suffix = 'prod'
        print("🚀 Creating PRODUCTION stacks")
    elif suffix == 'Dev':
        # 개발 환경
        stack_suffix = suffix
        domain_suffix = 'dev'
        print("🧪 Creating DEVELOPMENT stacks")
    else:
        continue

    # 1. 백엔드 스택 생성
    backend_stack = ChatbotStack(
        app, 
        f"ChatbotBackend{stack_suffix}",
        stack_name=f"ChatbotBackend{stack_suffix}",
        description=f"Chatbot System - {domain_suffix.upper()} Environment",
        env=env,
        tags={
            "Environment": domain_suffix,
            "Project": "Chatbot",
            "Owner": "CI/CD"
        }
    )

    # 2. 대화 기록 스택 생성
    conversation_stack = ChatbotConversationStack(
        app, 
        f"ChatbotConversationStack{stack_suffix}",
        stack_name=f"ChatbotConversationStack{stack_suffix}",
        description=f"Conversation Management System - {domain_suffix.upper()} Environment",
        env=env,
        tags={
            "Environment": domain_suffix,
            "Project": "Chatbot",
            "Owner": "CI/CD"
        }
    )

    # 대화 API를 기존 API Gateway에 추가
    conversation_stack.add_api_endpoints(backend_stack.api, backend_stack.api_authorizer)

    # 3. 프론트엔드 스택 생성
    frontend_stack = NewsSummarizerFrontendStack(
        app, 
        f"ChatbotFrontendStack{stack_suffix}",
        stack_name=f"ChatbotFrontendStack{stack_suffix}",
        api_gateway_url=backend_stack.api.url,
        rest_api=backend_stack.api,
        environment=domain_suffix,  # 환경 정보 전달
        env=env,
        tags={
            "Environment": domain_suffix,
            "Project": "Chatbot",
            "Owner": "CI/CD"
        }
    )

    # 스택 간 의존성 설정
    frontend_stack.add_dependency(backend_stack)
    frontend_stack.add_dependency(conversation_stack)

    print(f"✅ {domain_suffix.upper()} stacks configured:")
    print(f"   - Backend: ChatbotBackend{stack_suffix}")
    print(f"   - Conversation: ChatbotConversationStack{stack_suffix}")
    print(f"   - Frontend: ChatbotFrontendStack{stack_suffix}")

app.synth() 
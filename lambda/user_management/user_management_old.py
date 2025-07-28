#!/usr/bin/env python3
"""
User Management API Lambda Function
Handles user profiles, subscriptions, and usage tracking
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import boto3
from botocore.exceptions import ClientError
from decimal import Decimal

# Setup logging
logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('REGION', 'ap-northeast-2'))
cognito_client = boto3.client('cognito-idp', region_name=os.environ.get('REGION', 'ap-northeast-2'))

# 테이블 참조
users_table = dynamodb.Table(os.environ['USERS_TABLE'])
usage_table = dynamodb.Table(os.environ['USAGE_TABLE'])
subscriptions_table = dynamodb.Table(os.environ['SUBSCRIPTIONS_TABLE'])

# 환경변수
USER_POOL_ID = os.environ['USER_POOL_ID']

def handler(event, context):
    """Lambda 메인 핸들러"""
    try:
        # CORS 헤더
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
            'Content-Type': 'application/json'
        }
        
        # OPTIONS 요청 처리
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'OK'})
            }
        
        # 경로 파싱
        path = event.get('path', '')
        method = event.get('httpMethod', '')
        
        # 인증 정보 추출
        auth_context = event.get('requestContext', {}).get('authorizer', {})
        user_id = auth_context.get('claims', {}).get('sub')
        
        if not user_id:
            return {
                'statusCode': 401,
                'headers': headers,
                'body': json.dumps({'error': '인증이 필요합니다'})
            }
        
        logger.info(f"요청: {method} {path}, 사용자: {user_id}")
        
        # 라우팅
        if '/user/profile' in path:
            if method == 'GET':
                return get_user_profile(user_id, headers)
            elif method == 'PUT':
                return update_user_profile(user_id, event, headers)
                
        elif '/user/usage' in path:
            if method == 'GET':
                return get_user_usage(user_id, event, headers)
                
        elif '/user/subscription' in path:
            if method == 'GET':
                return get_user_subscription(user_id, headers)
            elif method == 'PUT':
                return update_user_subscription(user_id, event, headers)
        
        # 경로를 찾을 수 없음
        return {
            'statusCode': 404,
            'headers': headers,
            'body': json.dumps({'error': '경로를 찾을 수 없습니다'})
        }
        
    except Exception as e:
        logger.error(f"오류 발생: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({'error': '서버 오류가 발생했습니다'})
        }

def get_user_profile(user_id, headers):
    """사용자 프로필 조회"""
    try:
        # DynamoDB에서 사용자 정보 조회
        response = users_table.get_item(Key={'user_id': user_id})
        
        if 'Item' not in response:
            # 사용자 정보가 없으면 Cognito에서 생성
            return create_user_profile(user_id, headers)
        
        user_data = response['Item']
        
        # Decimal을 float로 변환
        user_data = decimal_to_float(user_data)
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(user_data)
        }
        
    except Exception as e:
        logger.error(f"사용자 프로필 조회 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': '프로필 조회에 실패했습니다'})
        }

def create_user_profile(user_id, headers):
    """새 사용자 프로필 생성"""
    try:
        # Cognito에서 사용자 정보 가져오기
        response = cognito_client.admin_get_user(
            UserPoolId=USER_POOL_ID,
            Username=user_id
        )
        
        email = None
        name = None
        
        # 사용자 속성에서 이메일과 이름 추출
        for attr in response.get('UserAttributes', []):
            if attr['Name'] == 'email':
                email = attr['Value']
            elif attr['Name'] == 'name':
                name = attr['Value']
        
        # 사용자 그룹 확인
        groups = []
        try:
            groups_response = cognito_client.admin_list_groups_for_user(
                UserPoolId=USER_POOL_ID,
                Username=user_id
            )
            groups = [group['GroupName'] for group in groups_response.get('Groups', [])]
        except Exception as e:
            logger.warning(f"그룹 조회 실패: {str(e)}")
        
        # 사용자 역할 결정
        user_role = 'admin' if 'admin' in groups else 'user'
        
        # 현재 시간
        now = datetime.utcnow().isoformat()
        
        # 사용자 데이터 생성
        user_data = {
            'user_id': user_id,
            'email': email,
            'name': name or email.split('@')[0] if email else 'Unknown',
            'user_role': user_role,
            'created_at': now,
            'updated_at': now,
            'status': 'active'
        }
        
        # DynamoDB에 저장
        users_table.put_item(Item=user_data)
        
        # 기본 구독 정보 생성
        subscription_data = {
            'user_id': user_id,
            'plan_type': 'free',
            'status': 'active',
            'start_date': now,
            'expiry_date': (datetime.utcnow() + timedelta(days=365)).isoformat(),
            'token_limit': 10000,
            'created_at': now,
            'updated_at': now
        }
        
        subscriptions_table.put_item(Item=subscription_data)
        
        logger.info(f"새 사용자 프로필 생성 완료: {user_id}")
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(user_data)
        }
        
    except Exception as e:
        logger.error(f"사용자 프로필 생성 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': '프로필 생성에 실패했습니다'})
        }

def update_user_profile(user_id, event, headers):
    """사용자 프로필 수정"""
    try:
        body = json.loads(event.get('body', '{}'))
        
        # 수정 가능한 필드들
        updateable_fields = ['name']
        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.utcnow().isoformat()}
        
        for field in updateable_fields:
            if field in body:
                update_expression += f", {field} = :{field}"
                expression_values[f':{field}'] = body[field]
        
        # 업데이트 실행
        users_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': '프로필이 업데이트되었습니다'})
        }
        
    except Exception as e:
        logger.error(f"사용자 프로필 수정 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': '프로필 수정에 실패했습니다'})
        }

def get_user_usage(user_id, event, headers):
    """사용자 사용량 조회"""
    try:
        # 쿼리 파라미터에서 기간 설정
        query_params = event.get('queryStringParameters') or {}
        period = query_params.get('period', 'month')  # day, week, month
        
        # 기간에 따른 날짜 계산
        end_date = datetime.utcnow()
        
        if period == 'day':
            start_date = end_date - timedelta(days=1)
        elif period == 'week':
            start_date = end_date - timedelta(weeks=1)
        else:  # month
            start_date = end_date - timedelta(days=30)
        
        # 사용량 데이터 조회
        response = usage_table.query(
            KeyConditionExpression='user_id = :user_id AND #date BETWEEN :start_date AND :end_date',
            ExpressionAttributeNames={'#date': 'date'},
            ExpressionAttributeValues={
                ':user_id': user_id,
                ':start_date': start_date.strftime('%Y-%m-%d'),
                ':end_date': end_date.strftime('%Y-%m-%d')
            }
        )
        
        # 데이터 집계
        total_tokens = 0
        total_requests = 0
        daily_usage = {}
        
        for item in response['Items']:
            item = decimal_to_float(item)
            date = item['date']
            tokens = item.get('token_used', 0)
            requests = item.get('request_count', 0)
            
            total_tokens += tokens
            total_requests += requests
            daily_usage[date] = {
                'tokens': tokens,
                'requests': requests
            }
        
        # 구독 정보에서 한도 조회
        subscription_response = subscriptions_table.get_item(Key={'user_id': user_id})
        token_limit = 0
        if 'Item' in subscription_response:
            token_limit = subscription_response['Item'].get('token_limit', 0)
        
        usage_data = {
            'period': period,
            'total_tokens': total_tokens,
            'total_requests': total_requests,
            'token_limit': token_limit,
            'usage_percentage': (total_tokens / token_limit * 100) if token_limit > 0 else 0,
            'daily_usage': daily_usage
        }
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(usage_data)
        }
        
    except Exception as e:
        logger.error(f"사용량 조회 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': '사용량 조회에 실패했습니다'})
        }

def get_user_subscription(user_id, headers):
    """사용자 구독 정보 조회"""
    try:
        response = subscriptions_table.get_item(Key={'user_id': user_id})
        
        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': headers,
                'body': json.dumps({'error': '구독 정보를 찾을 수 없습니다'})
            }
        
        subscription_data = decimal_to_float(response['Item'])
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps(subscription_data)
        }
        
    except Exception as e:
        logger.error(f"구독 정보 조회 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': '구독 정보 조회에 실패했습니다'})
        }

def update_user_subscription(user_id, event, headers):
    """사용자 구독 정보 수정 (관리자 전용)"""
    try:
        # 관리자 권한 확인
        auth_context = event.get('requestContext', {}).get('authorizer', {})
        groups = auth_context.get('claims', {}).get('cognito:groups', '').split(',')
        
        if 'admin' not in groups:
            return {
                'statusCode': 403,
                'headers': headers,
                'body': json.dumps({'error': '관리자 권한이 필요합니다'})
            }
        
        body = json.loads(event.get('body', '{}'))
        
        # 수정 가능한 필드들
        updateable_fields = ['plan_type', 'status', 'expiry_date', 'token_limit']
        update_expression = "SET updated_at = :updated_at"
        expression_values = {':updated_at': datetime.utcnow().isoformat()}
        
        for field in updateable_fields:
            if field in body:
                update_expression += f", {field} = :{field}"
                expression_values[f':{field}'] = body[field]
        
        # 업데이트 실행
        subscriptions_table.update_item(
            Key={'user_id': user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        return {
            'statusCode': 200,
            'headers': headers,
            'body': json.dumps({'message': '구독 정보가 업데이트되었습니다'})
        }
        
    except Exception as e:
        logger.error(f"구독 정보 수정 오류: {str(e)}")
        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({'error': '구독 정보 수정에 실패했습니다'})
        }

def record_usage(user_id, token_count, request_count=1):
    """사용량 기록 (다른 Lambda에서 호출)"""
    try:
        today = datetime.utcnow().strftime('%Y-%m-%d')
        month = datetime.utcnow().strftime('%Y-%m')
        
        # TTL 설정 (90일 후 자동 삭제)
        ttl = int((datetime.utcnow() + timedelta(days=90)).timestamp())
        
        # 기존 데이터 조회
        try:
            response = usage_table.get_item(
                Key={'user_id': user_id, 'date': today}
            )
            
            if 'Item' in response:
                # 기존 데이터 업데이트
                usage_table.update_item(
                    Key={'user_id': user_id, 'date': today},
                    UpdateExpression="ADD token_used :tokens, request_count :requests SET updated_at = :updated_at, #ttl = :ttl, #month = :month",
                    ExpressionAttributeNames={'#ttl': 'ttl', '#month': 'month'},
                    ExpressionAttributeValues={
                        ':tokens': Decimal(str(token_count)),
                        ':requests': Decimal(str(request_count)),
                        ':updated_at': datetime.utcnow().isoformat(),
                        ':ttl': ttl,
                        ':month': month
                    }
                )
            else:
                # 새 데이터 생성
                usage_table.put_item(
                    Item={
                        'user_id': user_id,
                        'date': today,
                        'month': month,
                        'token_used': Decimal(str(token_count)),
                        'request_count': Decimal(str(request_count)),
                        'created_at': datetime.utcnow().isoformat(),
                        'updated_at': datetime.utcnow().isoformat(),
                        'ttl': ttl
                    }
                )
        except Exception as e:
            logger.error(f"사용량 기록 오류: {str(e)}")
            
    except Exception as e:
        logger.error(f"사용량 기록 전체 오류: {str(e)}")

def decimal_to_float(data):
    """DynamoDB Decimal 타입을 float로 변환"""
    if isinstance(data, dict):
        return {k: decimal_to_float(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [decimal_to_float(item) for item in data]
    elif isinstance(data, Decimal):
        return float(data)
    else:
        return data 
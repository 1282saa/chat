import json
import boto3
import os
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
import urllib.parse
import sys
from decimal import Decimal
from pathlib import Path

# auth_utils 경로 추가
sys.path.append(str(Path(__file__).parent.parent / 'auth'))
sys.path.append(str(Path(__file__).parent.parent / 'utils'))

try:
    from auth_utils import extract_user_from_event, get_cors_headers
    from common_utils import DecimalEncoder
except ImportError:
    # auth_utils가 없는 경우 기본 구현
    def extract_user_from_event(event):
        return {'user_id': 'default', 'email': 'default@example.com'}
    
    def get_cors_headers():
        return {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
            'Access-Control-Max-Age': '86400'
        }
    
    # DecimalEncoder fallback
    class DecimalEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Decimal):
                if obj % 1 == 0:
                    return int(obj)
                else:
                    return float(obj)
            return super(DecimalEncoder, self).default(obj)

# 로깅 설정
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS 클라이언트 초기화
dynamodb = boto3.resource('dynamodb', region_name=os.environ['REGION'])
s3_client = boto3.client('s3', region_name=os.environ['REGION'])

# 환경 변수
PROJECT_TABLE = os.environ['PROJECT_TABLE']
PROMPT_BUCKET = os.environ['PROMPT_BUCKET']
REGION = os.environ['REGION']

# 🔧 추가: 카테고리 관리를 위한 DynamoDB 테이블
CATEGORY_TABLE = os.environ.get('CATEGORY_TABLE', PROJECT_TABLE)  # 같은 테이블 사용 또는 별도 테이블

# =============================================================================
# 카테고리 관리 함수들
# =============================================================================

def list_categories(event: Dict[str, Any]) -> Dict[str, Any]:
    """카테고리 목록 조회 - 단순화된 버전"""
    try:
        logger.info("카테고리 목록 조회 요청")
        
        # 빈 깡통 시스템 - 사용자가 직접 카테고리를 만들어야 함
        categories = []
        
        logger.info(f"카테고리 {len(categories)}개 반환")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'categories': categories,
                'count': len(categories)
            }, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"카테고리 목록 조회 실패: {str(e)}")
        return create_error_response(500, f"카테고리 목록 조회 실패: {str(e)}")

def create_category(event: Dict[str, Any]) -> Dict[str, Any]:
    """새 카테고리 생성"""
    try:
        body = json.loads(event['body']) if event.get('body') else {}
        category_name = body.get('name', '').strip()
        
        if not category_name:
            return create_error_response(400, "카테고리 이름이 필요합니다")
        
        # 사용자 정보 추출
        user = event.get('user', {})
        user_id = user.get('user_id', 'unknown')
        
        # 카테고리 ID 생성
        category_id = str(uuid.uuid4())
        
        # 카테고리 데이터 구성
        category_data = {
            'ownerId': user_id,
            'projectId': f"category#{category_id}",
            'name': category_name,
            'description': body.get('description', ''),
            'color': body.get('color', 'gray'),
            'icon': body.get('icon', '🔧'),
            'status': 'active',
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat()
        }
        
        # DynamoDB에 저장
        table = dynamodb.Table(PROJECT_TABLE)
        table.put_item(Item=category_data)
        
        logger.info(f"새 카테고리 생성: {category_id} - {category_name}")
        
        # 응답용 데이터 (category# 접두사 제거)
        response_category = {
            'id': category_id,
            'name': category_name,
            'description': category_data['description'],
            'color': category_data['color'],
            'icon': category_data['icon'],
            'createdAt': category_data['createdAt'],
            'updatedAt': category_data['updatedAt']
        }
        
        return {
            'statusCode': 201,
            'headers': get_cors_headers(),
            'body': json.dumps(response_category, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"카테고리 생성 실패: {str(e)}")
        return create_error_response(500, f"카테고리 생성 실패: {str(e)}")

def update_category(event: Dict[str, Any]) -> Dict[str, Any]:
    """카테고리 수정"""
    try:
        category_id = event['pathParameters']['categoryId']
        body = json.loads(event['body']) if event.get('body') else {}
        
        user = event.get('user', {})
        user_id = user.get('user_id', 'unknown')
        
        table = dynamodb.Table(PROJECT_TABLE)
        
        # 기존 카테고리 확인
        response = table.get_item(Key={
            'ownerId': user_id,
            'projectId': f"category#{category_id}"
        })
        
        if 'Item' not in response:
            return create_error_response(404, "카테고리를 찾을 수 없습니다")
        
        # 업데이트할 필드들
        update_expression = "SET #updatedAt = :updatedAt"
        expression_attribute_names = {'#updatedAt': 'updatedAt'}
        expression_attribute_values = {':updatedAt': datetime.utcnow().isoformat()}
        
        if 'name' in body:
            update_expression += ", #name = :name"
            expression_attribute_names['#name'] = 'name'
            expression_attribute_values[':name'] = body['name']
        
        if 'description' in body:
            update_expression += ", #description = :description"
            expression_attribute_names['#description'] = 'description'
            expression_attribute_values[':description'] = body['description']
        
        if 'color' in body:
            update_expression += ", #color = :color"
            expression_attribute_names['#color'] = 'color'
            expression_attribute_values[':color'] = body['color']
        
        if 'icon' in body:
            update_expression += ", #icon = :icon"
            expression_attribute_names['#icon'] = 'icon'
            expression_attribute_values[':icon'] = body['icon']
        
        # 업데이트 실행
        table.update_item(
            Key={
                'ownerId': user_id,
                'projectId': f"category#{category_id}"
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
        # 업데이트된 카테고리 조회
        updated_response = table.get_item(Key={
            'ownerId': user_id,
            'projectId': f"category#{category_id}"
        })
        
        updated_category = {
            'id': category_id,
            'name': updated_response['Item']['name'],
            'description': updated_response['Item'].get('description', ''),
            'color': updated_response['Item'].get('color', 'gray'),
            'icon': updated_response['Item'].get('icon', '🔧'),
            'createdAt': updated_response['Item'].get('createdAt', ''),
            'updatedAt': updated_response['Item']['updatedAt']
        }
        
        logger.info(f"카테고리 수정: {category_id}")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(updated_category, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"카테고리 수정 실패: {str(e)}")
        return create_error_response(500, f"카테고리 수정 실패: {str(e)}")

def delete_category(event: Dict[str, Any]) -> Dict[str, Any]:
    """카테고리 삭제"""
    try:
        category_id = event['pathParameters']['categoryId']
        user = event.get('user', {})
        user_id = user.get('user_id', 'unknown')
        
        table = dynamodb.Table(PROJECT_TABLE)
        
        # 기존 카테고리 확인
        response = table.get_item(Key={
            'ownerId': user_id,
            'projectId': f"category#{category_id}"
        })
        
        if 'Item' not in response:
            return create_error_response(404, "카테고리를 찾을 수 없습니다")
        
        # 해당 카테고리를 사용하는 프로젝트가 있는지 확인
        projects_response = table.scan(
            FilterExpression='#ownerId = :ownerId AND #category = :category AND NOT begins_with(#projectId, :category_prefix)',
            ExpressionAttributeNames={
                '#ownerId': 'ownerId',
                '#category': 'category',
                '#projectId': 'projectId'
            },
            ExpressionAttributeValues={
                ':ownerId': user_id,
                ':category': category_id,
                ':category_prefix': 'category#'
            }
        )
        
        if projects_response.get('Items'):
            return create_error_response(400, "이 카테고리를 사용하는 프로젝트가 있어 삭제할 수 없습니다")
        
        # 카테고리 삭제
        table.delete_item(Key={
            'ownerId': user_id,
            'projectId': f"category#{category_id}"
        })
        
        logger.info(f"카테고리 삭제: {category_id}")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': '카테고리가 삭제되었습니다',
                'categoryId': category_id
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        logger.error(f"카테고리 삭제 실패: {str(e)}")
        return create_error_response(500, f"카테고리 삭제 실패: {str(e)}")

# =============================================================================
# 기존 프로젝트 관리 함수들
# =============================================================================

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    프로젝트 및 카테고리 관리 메인 핸들러
    
    Routes:
    - POST /projects: 새 프로젝트 생성
    - GET /projects: 프로젝트 목록 조회
    - GET /projects/{id}: 프로젝트 상세 조회
    - GET /projects/{id}/upload-url: 파일 업로드용 pre-signed URL 생성
    - GET /categories: 사용자 카테고리 목록 조회
    - POST /categories: 새 카테고리 생성
    - PUT /categories/{id}: 카테고리 수정
    - DELETE /categories/{id}: 카테고리 삭제
    """
    try:
        logger.info(f"프로젝트/카테고리 요청 수신: {json.dumps(event, indent=2)}")
        
        http_method = event.get('httpMethod', 'GET')
        path = event.get('path', '')
        resource = event.get('resource', '')
        path_parameters = event.get('pathParameters', {}) or {}
        
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
        
        # 카테고리 관련 라우팅
        if '/categories' in path or '/categories' in resource:
            if path_parameters.get('categoryId'):
                # 개별 카테고리 작업
                if http_method == 'PUT':
                    return update_category(event)
                elif http_method == 'DELETE':
                    return delete_category(event)
                else:
                    return create_error_response(405, "지원하지 않는 메소드입니다")
            else:
                # 카테고리 목록 작업
                if http_method == 'GET':
                    return list_categories(event)
                elif http_method == 'POST':
                    return create_category(event)
                else:
                    return create_error_response(405, "지원하지 않는 메소드입니다")
        
        # 기존 프로젝트 관련 라우팅
        elif 'upload-url' in resource:
            return get_upload_url(event)
        elif path_parameters.get('projectId'):
            if http_method == 'GET':
                return get_project(event)
            elif http_method == 'PUT':
                return update_project(event)
            elif http_method == 'DELETE':
                return delete_project(event)
            else:
                return create_error_response(405, "지원하지 않는 메소드입니다")
        elif http_method == 'POST':
            return create_project(event)
        elif http_method == 'GET':
            return list_projects(event)
        else:
            return create_error_response(405, "지원하지 않는 메소드입니다")
            
    except Exception as e:
        logger.error(f"프로젝트/카테고리 처리 중 오류 발생: {str(e)}")
        # 예외 발생 시에도 CORS 헤더 포함
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'error': f"내부 서버 오류: {str(e)}",
                'timestamp': datetime.utcnow().isoformat()
            }, ensure_ascii=False)
        }

def create_project(event: Dict[str, Any]) -> Dict[str, Any]:
    """새 프로젝트 생성"""
    try:
        body = json.loads(event['body']) if event.get('body') else {}
        project_name = body.get('name', '').strip()
        
        if not project_name:
            return create_error_response(400, "프로젝트 이름이 필요합니다")
        
        # 프로젝트 ID 생성
        project_id = str(uuid.uuid4())
        
        # 프로젝트 데이터 구성 (인증 정보 제거)
        project_data = {
            'projectId': project_id,
            'name': project_name,
            'description': body.get('description', ''),
            'status': 'active',
            'createdAt': datetime.utcnow().isoformat(),
            'updatedAt': datetime.utcnow().isoformat(),
            'promptCount': 0,
            'conversationCount': 0,
            'tags': body.get('tags', []),
            # AI 커스터마이징 필드들
            'aiRole': body.get('aiRole', ''),
            'aiInstructions': body.get('aiInstructions', ''),
            'targetAudience': body.get('targetAudience', '일반독자'),
            'outputFormat': body.get('outputFormat', 'multiple'),
            'styleGuidelines': body.get('styleGuidelines', '')
        }
        
        # DynamoDB에 저장
        table = dynamodb.Table(PROJECT_TABLE)
        table.put_item(Item=project_data)
        
        logger.info(f"새 프로젝트 생성: {project_id} - {project_name}")
        
        return {
            'statusCode': 201,
            'headers': get_cors_headers(),
            'body': json.dumps(project_data, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"프로젝트 생성 실패: {str(e)}")
        return create_error_response(500, f"프로젝트 생성 실패: {str(e)}")

def list_projects(event: Dict[str, Any]) -> Dict[str, Any]:
    """프로젝트 목록 조회 (사용자별 필터링)"""
    try:
        query_params = event.get('queryStringParameters') or {}
        
        # 사용자 정보 추출
        user = event.get('user', {})
        user_id = user.get('user_id', 'unknown')
        
        # 페이지네이션 파라미터
        limit = int(query_params.get('limit', 20))
        last_evaluated_key = query_params.get('lastKey')
        
        # 상태 필터 - 삭제된 프로젝트도 포함하도록 수정
        status_filter = query_params.get('status', 'all')  # 기본값을 'all'로 변경
        
        table = dynamodb.Table(PROJECT_TABLE)
        
        # 스캔 파라미터 구성 - 카테고리가 아닌 실제 프로젝트만 조회
        if status_filter == 'all':
            scan_params = {
                'Limit': limit,
                'FilterExpression': 'NOT begins_with(#projectId, :category_prefix)',
                'ExpressionAttributeNames': {
                    '#projectId': 'projectId'
                },
                'ExpressionAttributeValues': {
                    ':category_prefix': 'category#'
                }
            }
        else:
            scan_params = {
                'Limit': limit,
                'FilterExpression': '#status = :status AND NOT begins_with(#projectId, :category_prefix)',
                'ExpressionAttributeNames': {
                    '#status': 'status',
                    '#projectId': 'projectId'
                },
                'ExpressionAttributeValues': {
                    ':status': status_filter,
                    ':category_prefix': 'category#'
                }
            }
        
        if last_evaluated_key:
            scan_params['ExclusiveStartKey'] = {'projectId': last_evaluated_key}
        
        response = table.scan(**scan_params)
        
        # 결과 정렬 (최신순)
        projects = sorted(response['Items'], key=lambda x: x['createdAt'], reverse=True)
        
        result = {
            'projects': projects,
            'count': len(projects),
            'hasMore': 'LastEvaluatedKey' in response
        }
        
        if 'LastEvaluatedKey' in response:
            result['nextKey'] = response['LastEvaluatedKey']['projectId']
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(result, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"프로젝트 목록 조회 실패: {str(e)}")
        return create_error_response(500, f"프로젝트 목록 조회 실패: {str(e)}")

def get_project(event: Dict[str, Any]) -> Dict[str, Any]:
    """프로젝트 상세 조회 (인증 로직 제거, 삭제된 프로젝트도 조회 가능)"""
    try:
        project_id = event['pathParameters']['projectId']
        
        table = dynamodb.Table(PROJECT_TABLE)
        
        # 프로젝트 검색 - 삭제된 프로젝트도 포함
        response = table.scan(
            FilterExpression='#projectId = :projectId AND NOT begins_with(#projectId, :category_prefix)',
            ExpressionAttributeNames={
                '#projectId': 'projectId'
            },
            ExpressionAttributeValues={
                ':projectId': project_id,
                ':category_prefix': 'category#'
            }
        )
        
        if not response.get('Items'):
            return create_error_response(404, "프로젝트를 찾을 수 없습니다")
        
        project = response['Items'][0]
        
        # 삭제된 프로젝트인 경우 상태를 active로 변경하여 접근 가능하게 함
        if project.get('status') == 'deleted':
            logger.info(f"삭제된 프로젝트 {project_id}를 active 상태로 복원")
            table.update_item(
                Key={'projectId': project_id},
                UpdateExpression="SET #status = :status, updatedAt = :updatedAt",
                ExpressionAttributeNames={'#status': 'status'},
                ExpressionAttributeValues={
                    ':status': 'active',
                    ':updatedAt': datetime.utcnow().isoformat()
                }
            )
            project['status'] = 'active'
        
        # 프롬프트 정보 추가 조회
        project['prompts'] = get_project_prompts(project_id)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(project, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"프로젝트 조회 실패: {str(e)}")
        return create_error_response(500, f"프로젝트 조회 실패: {str(e)}")

def update_project(event: Dict[str, Any]) -> Dict[str, Any]:
    """프로젝트 업데이트"""
    try:
        project_id = event['pathParameters']['projectId']
        body = json.loads(event['body']) if event.get('body') else {}
        
        # 업데이트 가능한 필드들
        update_fields = ['name', 'description', 'tags', 'status', 'aiRole', 'aiInstructions', 'targetAudience', 'outputFormat', 'styleGuidelines']
        update_expression = "SET updatedAt = :updatedAt"
        expression_values = {':updatedAt': datetime.utcnow().isoformat()}
        
        for field in update_fields:
            if field in body:
                update_expression += f", {field} = :{field}"
                expression_values[f':{field}'] = body[field]
        
        table = dynamodb.Table(PROJECT_TABLE)
        
        # 먼저 프로젝트 존재 여부 확인
        scan_response = table.scan(
            FilterExpression='#projectId = :projectId AND NOT begins_with(#projectId, :category_prefix)',
            ExpressionAttributeNames={
                '#projectId': 'projectId'
            },
            ExpressionAttributeValues={
                ':projectId': project_id,
                ':category_prefix': 'category#'
            }
        )
        
        if not scan_response.get('Items'):
            return create_error_response(404, "프로젝트를 찾을 수 없습니다")
        
        response = table.update_item(
            Key={'projectId': project_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnValues='ALL_NEW'
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(response['Attributes'], ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"프로젝트 업데이트 실패: {str(e)}")
        return create_error_response(500, f"프로젝트 업데이트 실패: {str(e)}")

def delete_project(event: Dict[str, Any]) -> Dict[str, Any]:
    """프로젝트 삭제"""
    try:
        project_id = event['pathParameters']['projectId']
        
        # 프로젝트 존재 확인
        table = dynamodb.Table(PROJECT_TABLE)
        scan_response = table.scan(
            FilterExpression='#projectId = :projectId AND NOT begins_with(#projectId, :category_prefix)',
            ExpressionAttributeNames={
                '#projectId': 'projectId'
            },
            ExpressionAttributeValues={
                ':projectId': project_id,
                ':category_prefix': 'category#'
            }
        )
        
        if not scan_response.get('Items'):
            return create_error_response(404, "프로젝트를 찾을 수 없습니다")
        
        # 소프트 삭제 (상태를 'deleted'로 변경)
        table.update_item(
            Key={'projectId': project_id},
            UpdateExpression="SET #status = :status, updatedAt = :updatedAt",
            ExpressionAttributeNames={'#status': 'status'},
            ExpressionAttributeValues={
                ':status': 'deleted',
                ':updatedAt': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"프로젝트 삭제: {project_id}")
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'message': '프로젝트가 삭제되었습니다'}, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"프로젝트 삭제 실패: {str(e)}")
        return create_error_response(500, f"프로젝트 삭제 실패: {str(e)}")

def get_upload_url(event: Dict[str, Any]) -> Dict[str, Any]:
    """프롬프트 파일 업로드용 pre-signed URL 생성"""
    try:
        project_id = event['pathParameters']['projectId']
        query_params = event.get('queryStringParameters') or {}
        
        category = query_params.get('category', '')
        filename = query_params.get('filename', '')
        
        if not category or not filename:
            return create_error_response(400, "카테고리와 파일명이 필요합니다")
        
        # S3 키 생성: {projectId}/{category}/{filename}
        s3_key = f"{project_id}/{category}/{filename}"
        
        # Pre-signed URL 생성
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': PROMPT_BUCKET,
                'Key': s3_key,
                'ContentType': 'text/plain'
            },
            ExpiresIn=3600  # 1시간
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'uploadUrl': presigned_url,
                's3Key': s3_key,
                'bucket': PROMPT_BUCKET,
                'expiresIn': 3600
            }, ensure_ascii=False, cls=DecimalEncoder)
        }
        
    except Exception as e:
        logger.error(f"업로드 URL 생성 실패: {str(e)}")
        return create_error_response(500, f"업로드 URL 생성 실패: {str(e)}")

def get_project_prompts(project_id: str) -> List[Dict[str, Any]]:
    """프로젝트의 프롬프트 메타데이터 조회"""
    try:
        # 실제 구현에서는 PROMPT_META_TABLE을 사용
        # 현재는 간단하게 빈 리스트 반환
        return []
        
    except Exception as e:
        logger.error(f"프롬프트 조회 실패: {str(e)}")
        return []

def get_cors_headers() -> Dict[str, str]:
    """CORS 헤더 반환"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With'
    }

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """에러 응답 생성"""
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'error': message,
            'timestamp': datetime.utcnow().isoformat()
        }, ensure_ascii=False, cls=DecimalEncoder)
    } 
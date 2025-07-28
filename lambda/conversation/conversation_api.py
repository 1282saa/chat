import json
import boto3
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
conversations_table = dynamodb.Table(os.environ['CONVERSATIONS_TABLE'])
messages_table = dynamodb.Table(os.environ['MESSAGES_TABLE'])

def handler(event, context):
    """
    Handle conversation-related API requests
    GET /conversations - List user's conversations with pagination
    POST /conversations - Create new conversation
    DELETE /conversations/{id} - Delete a conversation
    PUT /conversations/{id} - Update conversation (title, etc.)
    """
    
    try:
        http_method = event['httpMethod']
        path = event['path']
        
        # Extract user info from Cognito JWT
        try:
            authorizer = event['requestContext']['authorizer']
            user_sub = authorizer.get('userId') or authorizer.get('principalId')
            user_email = authorizer.get('email')
            
            if not user_sub:
                raise ValueError("User sub not found in authorizer")
                
            print(f"Authenticated user: {user_sub} ({user_email})")
        except Exception as e:
            print(f"Authentication error: {str(e)}")
            print(f"Event requestContext: {event.get('requestContext', {})}")
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
                },
                'body': json.dumps({'error': 'Authentication required'})
            }
        
        print(f"요청: {http_method} {path}, 사용자: {user_sub}")
        print(f"DEBUG - Full user claims: {event.get('requestContext', {}).get('authorizer', {}).get('claims', {})}")
        print(f"DEBUG - User email: {event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('email', 'N/A')}")
        
        # 라우팅 로직
        if http_method == 'GET' and path == '/conversations':
            return get_conversations(user_sub, event.get('queryStringParameters') or {})
        elif http_method == 'POST' and path == '/conversations':
            return create_conversation(user_sub, json.loads(event['body']) if event.get('body') else {})
        elif http_method == 'DELETE' and path.startswith('/conversations/'):
            conversation_id = path.split('/')[-1]  # /conversations/{id}에서 id 추출
            return delete_conversation(user_sub, conversation_id)
        elif http_method == 'PUT' and path.startswith('/conversations/'):
            conversation_id = path.split('/')[-1]  # /conversations/{id}에서 id 추출
            body = json.loads(event.get('body', '{}'))
            return update_conversation(user_sub, conversation_id, body)
        else:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,DELETE,PUT,OPTIONS'
                },
                'body': json.dumps({'error': 'Not found'})
            }
            
    except Exception as e:
        print(f"Error in conversation handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': 'Internal server error'})
        }

def get_conversations(user_sub: str, query_params: Dict) -> Dict:
    """
    Get user's conversations with pagination
    Query params: limit (default 20), cursor (ISO timestamp for pagination)
    """
    
    limit = min(int(query_params.get('limit', 20)), 50)  # Max 50 conversations
    cursor = query_params.get('cursor')
    
    try:
        print(f"DEBUG - 대화 목록 조회 시작: user_sub={user_sub}")
        print(f"DEBUG - GSI1PK 값: USER#{user_sub}")
        
        # Query conversations using GSI
        query_kwargs = {
            'IndexName': 'GSI1-LastActivity',
            'KeyConditionExpression': 'GSI1PK = :pk',
            'ExpressionAttributeValues': {
                ':pk': f'USER#{user_sub}'
            },
            'ScanIndexForward': False,  # Most recent first
            'Limit': limit + 1  # Get one extra to determine if there are more
        }
        
        if cursor:
            try:
                # cursor should be in format "lastActivityAt:conversationId"
                if ':' in cursor:
                    last_activity, conv_id = cursor.split(':', 1)
                    query_kwargs['ExclusiveStartKey'] = {
                        'GSI1PK': f'USER#{user_sub}',
                        'lastActivityAt': last_activity,
                        'PK': f'USER#{user_sub}',
                        'SK': f'CONV#{conv_id}'
                    }
                else:
                    # Fallback: treat cursor as lastActivityAt only
                    print(f"Warning: Invalid cursor format: {cursor}")
            except Exception as e:
                print(f"Error parsing cursor: {e}")
                # Continue without cursor for pagination
        
        response = conversations_table.query(**query_kwargs)
        items = response.get('Items', [])
        
        print(f"DEBUG - DynamoDB 쿼리 결과: {len(items)}개 대화 발견")
        for item in items:
            print(f"DEBUG - 대화: PK={item.get('PK')}, SK={item.get('SK')}, title={item.get('title')}")
        
        # Check if there are more items
        has_more = len(items) > limit
        if has_more:
            items = items[:-1]  # Remove the extra item
        
        # Format conversations
        conversations = []
        for item in items:
            conversations.append({
                'id': item['SK'].replace('CONV#', ''),
                'title': item.get('title', 'New Conversation'),
                'startedAt': item.get('startedAt'),
                'lastActivityAt': item.get('lastActivityAt'),
                'tokenSum': int(item.get('tokenSum', 0))
            })
        
        # Prepare next cursor
        next_cursor = None
        if has_more and conversations:
            last_conv = conversations[-1]
            next_cursor = f"{last_conv['lastActivityAt']}:{last_conv['id']}"
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({
                'conversations': conversations,
                'nextCursor': next_cursor,
                'hasMore': has_more
            }, default=str)
        }
    
    except Exception as e:
        print(f"Error getting conversations: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization', 
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': 'Failed to retrieve conversations'})
        }

def create_conversation(user_sub: str, body: Dict) -> Dict:
    """
    Create a new conversation
    Body: { title?: string }
    """
    
    try:
        conv_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        title = body.get('title', 'New Conversation')
        
        # Calculate TTL (30 days from now)
        ttl = int((datetime.now(timezone.utc).timestamp()) + (30 * 24 * 60 * 60))
        
        # Create conversation item
        conversation_item = {
            'PK': f'USER#{user_sub}',
            'SK': f'CONV#{conv_id}',
            'GSI1PK': f'USER#{user_sub}',  # For GSI queries
            'title': title,
            'startedAt': now,
            'lastActivityAt': now,
            'tokenSum': 0,
            'ttl': ttl
        }
        
        conversations_table.put_item(Item=conversation_item)
        
        return {
            'statusCode': 201,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({
                'conversationId': conv_id,
                'title': title,
                'startedAt': now,
                'lastActivityAt': now
            })
        }
        
    except Exception as e:
        print(f"Error creating conversation: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
            },
            'body': json.dumps({'error': 'Failed to create conversation'})
        }

def update_conversation_activity(conv_id: str, user_sub: str, token_count: int = 0, title: str = None):
    """
    Update conversation's last activity and token sum
    This function will be called from WebSocket handler
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        update_expression = "SET lastActivityAt = :activity, tokenSum = tokenSum + :tokens"
        expression_values = {
            ':activity': now,
            ':tokens': token_count
        }
        
        if title:
            update_expression += ", title = :title"
            expression_values[':title'] = title
        
        conversations_table.update_item(
            Key={
                'PK': f'USER#{user_sub}',
                'SK': f'CONV#{conv_id}'
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        return True
        
    except Exception as e:
        print(f"Error updating conversation activity: {str(e)}")
        return False


def delete_conversation(user_sub: str, conversation_id: str) -> Dict:
    """
    Delete a conversation and all its messages
    """
    try:
        print(f"대화 삭제 시작: user={user_sub}, conv_id={conversation_id}")
        
        # 1. 먼저 대화가 존재하고 사용자 소유인지 확인
        conversation_key = {
            'PK': f'USER#{user_sub}',
            'SK': f'CONV#{conversation_id}'
        }
        
        try:
            conversation_response = conversations_table.get_item(Key=conversation_key)
            if 'Item' not in conversation_response:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                        'Access-Control-Allow-Methods': 'GET,POST,DELETE,PUT,OPTIONS'
                    },
                    'body': json.dumps({'error': '대화를 찾을 수 없습니다'})
                }
        except Exception as e:
            print(f"Error checking conversation existence: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,DELETE,PUT,OPTIONS'
                },
                'body': json.dumps({'error': '대화 확인 중 오류가 발생했습니다'})
            }
        
        # 2. 관련된 모든 메시지 삭제 (배치 삭제)
        try:
            # 메시지들을 페이지네이션으로 조회하면서 삭제
            deleted_messages = 0
            last_evaluated_key = None
            
            while True:
                query_kwargs = {
                    'KeyConditionExpression': 'PK = :pk',
                    'ExpressionAttributeValues': {
                        ':pk': f'CONV#{conversation_id}'
                    },
                    'Limit': 25  # 배치 삭제를 위한 제한
                }
                
                if last_evaluated_key:
                    query_kwargs['ExclusiveStartKey'] = last_evaluated_key
                
                messages_response = messages_table.query(**query_kwargs)
                messages = messages_response.get('Items', [])
                
                if not messages:
                    break
                
                # 배치 삭제 처리
                with messages_table.batch_writer() as batch:
                    for message in messages:
                        batch.delete_item(Key={
                            'PK': message['PK'],
                            'SK': message['SK']
                        })
                        deleted_messages += 1
                
                last_evaluated_key = messages_response.get('LastEvaluatedKey')
                if not last_evaluated_key:
                    break
            
            print(f"삭제된 메시지 수: {deleted_messages}")
            
        except Exception as e:
            print(f"Error deleting messages: {str(e)}")
            # 메시지 삭제 실패해도 대화는 삭제 진행
        
        # 3. 대화 메타데이터 삭제
        conversations_table.delete_item(Key=conversation_key)
        
        print(f"대화 삭제 완료: {conversation_id}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,DELETE,PUT,OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'message': '대화가 성공적으로 삭제되었습니다',
                'deletedMessages': deleted_messages if 'deleted_messages' in locals() else 0
            })
        }
        
    except Exception as e:
        print(f"Error deleting conversation: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,DELETE,PUT,OPTIONS'
            },
            'body': json.dumps({'error': '대화 삭제 중 오류가 발생했습니다'})
        }


def update_conversation(user_sub: str, conversation_id: str, updates: Dict) -> Dict:
    """
    Update conversation properties (title, etc.)
    """
    try:
        print(f"대화 업데이트: user={user_sub}, conv_id={conversation_id}, updates={updates}")
        
        # 1. 대화가 존재하고 사용자 소유인지 확인
        conversation_key = {
            'PK': f'USER#{user_sub}',
            'SK': f'CONV#{conversation_id}'
        }
        
        try:
            conversation_response = conversations_table.get_item(Key=conversation_key)
            if 'Item' not in conversation_response:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                        'Access-Control-Allow-Methods': 'GET,POST,DELETE,PUT,OPTIONS'
                    },
                    'body': json.dumps({'error': '대화를 찾을 수 없습니다'})
                }
        except Exception as e:
            print(f"Error checking conversation existence: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                    'Access-Control-Allow-Methods': 'GET,POST,DELETE,PUT,OPTIONS'
                },
                'body': json.dumps({'error': '대화 확인 중 오류가 발생했습니다'})
            }
        
        # 2. 업데이트 표현식 구성
        update_expression = "SET lastActivityAt = :activity"
        expression_values = {
            ':activity': datetime.now(timezone.utc).isoformat()
        }
        
        # 업데이트 가능한 필드들
        if 'title' in updates and updates['title'].strip():
            update_expression += ", title = :title"
            expression_values[':title'] = updates['title'].strip()
        
        # 3. 업데이트 실행
        conversations_table.update_item(
            Key=conversation_key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values
        )
        
        print(f"대화 업데이트 완료: {conversation_id}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,DELETE,PUT,OPTIONS'
            },
            'body': json.dumps({
                'success': True,
                'message': '대화가 성공적으로 업데이트되었습니다',
                'conversationId': conversation_id
            })
        }
        
    except Exception as e:
        print(f"Error updating conversation: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'GET,POST,DELETE,PUT,OPTIONS'
            },
            'body': json.dumps({'error': '대화 업데이트 중 오류가 발생했습니다'})
        }
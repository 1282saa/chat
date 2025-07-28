from aws_cdk import (
    Duration,
    Stack,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_iam as iam,
    RemovalPolicy
)
from constructs import Construct

class ChatbotConversationStack(Stack):
    """
    CDK Stack for Conversation History functionality
    - DynamoDB tables for Conversations and Messages
    - Lambda functions for conversation APIs
    - API Gateway endpoints
    """

    def __init__(self, scope: Construct, construct_id: str, environment_suffix: str = "", **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # 환경별 테이블 이름 접미사
        self.environment_suffix = environment_suffix
        self.table_suffix = f"-{environment_suffix}" if environment_suffix else ""

        # DynamoDB Tables
        self.conversations_table = self._create_conversations_table()
        self.messages_table = self._create_messages_table()
        
        # Lambda Functions
        self.conversation_lambda = self._create_conversation_lambda()
        self.message_lambda = self._create_message_lambda()
        
        # API Gateway endpoints will be added to existing API
        
    def _create_conversations_table(self) -> dynamodb.Table:
        """Create Conversations table with GSI for user queries"""
        table = dynamodb.Table(
            self, "ConversationsTable",
            table_name=f"ChatbotConversations{self.table_suffix}",  # 환경별 고유 이름
            partition_key=dynamodb.Attribute(
                name="PK",  # USER#<cognito_sub>
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",  # CONV#<uuid>
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            time_to_live_attribute="ttl"
        )
        
        # GSI for querying conversations by user
        table.add_global_secondary_index(
            index_name="UserConversationsIndex",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt",
                type=dynamodb.AttributeType.STRING
            )
        )
        
        return table
    
    def _create_messages_table(self) -> dynamodb.Table:
        """Create Messages table for storing conversation messages"""
        table = dynamodb.Table(
            self, "MessagesTable", 
            table_name=f"ChatbotMessages{self.table_suffix}",  # 환경별 고유 이름
            partition_key=dynamodb.Attribute(
                name="PK",  # CONV#<uuid>
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK",  # TS#<iso_timestamp>
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.RETAIN,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            ),
            time_to_live_attribute="ttl"
        )
        
        return table
    
    def _create_conversation_lambda(self) -> _lambda.Function:
        """Lambda for conversation management (GET /conversations, POST /conversation)"""
        lambda_function = _lambda.Function(
            self, "ConversationFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("../lambda/conversation"),
            handler="conversation_api.handler",
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "CONVERSATIONS_TABLE": self.conversations_table.table_name,
                "MESSAGES_TABLE": self.messages_table.table_name
            }
        )
        
        # Grant permissions to DynamoDB tables
        self.conversations_table.grant_read_write_data(lambda_function)
        self.messages_table.grant_read_write_data(lambda_function)  # 메시지 삭제를 위해 write 권한 필요
        
        return lambda_function
    
    def _create_message_lambda(self) -> _lambda.Function:
        """Lambda for message management (GET /messages)"""
        lambda_function = _lambda.Function(
            self, "MessageFunction",
            runtime=_lambda.Runtime.PYTHON_3_11,
            code=_lambda.Code.from_asset("../lambda/message"),
            handler="message_api.handler", 
            timeout=Duration.seconds(30),
            memory_size=512,
            environment={
                "MESSAGES_TABLE": self.messages_table.table_name,
                "CONVERSATIONS_TABLE": self.conversations_table.table_name
            }
        )
        
        # Grant permissions to DynamoDB tables
        self.messages_table.grant_read_write_data(lambda_function)
        self.conversations_table.grant_read_write_data(lambda_function)
        
        return lambda_function
    
    def _create_cors_options_method(self, resource, allowed_methods):
        """CORS OPTIONS 메소드 생성 (기존 스택과 동일)"""
        return resource.add_method(
            "OPTIONS",
            apigateway.MockIntegration(
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        response_parameters={
                            "method.response.header.Access-Control-Allow-Headers": "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                            "method.response.header.Access-Control-Allow-Methods": f"'{allowed_methods}'",
                            "method.response.header.Access-Control-Allow-Origin": "'*'"
                        }
                    )
                ],
                request_templates={"application/json": '{"statusCode": 200}'}
            ),
            method_responses=[
                apigateway.MethodResponse(
                    status_code="200",
                    response_parameters={
                        "method.response.header.Access-Control-Allow-Headers": True,
                        "method.response.header.Access-Control-Allow-Methods": True,
                        "method.response.header.Access-Control-Allow-Origin": True
                    }
                )
            ],
            authorization_type=apigateway.AuthorizationType.NONE
        )
    
    def _add_gateway_responses(self, api: apigateway.RestApi):
        """Add Gateway Responses for CORS on errors"""
        cors_headers = {
            "method.response.header.Access-Control-Allow-Origin": "'*'",
            "method.response.header.Access-Control-Allow-Headers": "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
            "method.response.header.Access-Control-Allow-Methods": "'GET,POST,PUT,DELETE,OPTIONS'"
        }
        
        # Add CORS headers to common error responses
        api.add_gateway_response(
            "cors-4xx",
            type=apigateway.ResponseType.DEFAULT_4_XX,
            response_headers=cors_headers
        )
        
        api.add_gateway_response(
            "cors-5xx", 
            type=apigateway.ResponseType.DEFAULT_5_XX,
            response_headers=cors_headers
        )
        
        api.add_gateway_response(
            "cors-unauthorized",
            type=apigateway.ResponseType.UNAUTHORIZED,
            response_headers=cors_headers
        )

    def add_api_endpoints(self, api: apigateway.RestApi, authorizer: apigateway.IAuthorizer):
        """Add conversation endpoints to existing API Gateway"""
        
        # /conversations endpoint
        conversations_resource = api.root.add_resource("conversations")
        conversations_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.conversation_lambda),
            authorizer=authorizer
        )
        conversations_resource.add_method(
            "POST", 
            apigateway.LambdaIntegration(self.conversation_lambda),
            authorizer=authorizer
        )
        
        # /conversations/{id} endpoint for individual conversation operations
        conversation_id_resource = conversations_resource.add_resource("{id}")
        conversation_id_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.conversation_lambda),
            authorizer=authorizer
        )
        conversation_id_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.conversation_lambda),
            authorizer=authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(conversations_resource, "GET,POST,OPTIONS")
        self._create_cors_options_method(conversation_id_resource, "DELETE,PUT,OPTIONS")
        
        # /messages endpoint
        messages_resource = api.root.add_resource("messages")
        messages_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.message_lambda),
            authorizer=authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(messages_resource, "GET,OPTIONS")
        
        # Add Gateway Responses for CORS on errors
        self._add_gateway_responses(api)
import time
from aws_cdk import (
    Stack,
    aws_s3 as s3,
    aws_dynamodb as dynamodb,
    aws_lambda as lambda_,
    aws_apigateway as apigateway,
    aws_apigatewayv2 as apigatewayv2,
    aws_apigatewayv2_integrations as integrations,
    aws_iam as iam,
    aws_s3_notifications as s3_notifications,
    aws_cloudwatch as cloudwatch,
    aws_stepfunctions as stepfunctions,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_budgets as budgets,
    aws_bedrock as bedrock,
    aws_sqs as sqs,
    aws_cognito as cognito,
    aws_ec2 as ec2,
    RemovalPolicy,
    Duration,
    CfnOutput,
    BundlingOptions
)
from constructs import Construct
import json

class ChatbotStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # 1. Cognito 사용자 풀 생성
        self.create_cognito_user_pool()
        
        # 2. S3 버킷들 생성
        self.create_s3_buckets()
        
        # 3. DynamoDB 테이블들 생성
        self.create_dynamodb_tables()
        
        # 4. SQS DLQ 생성
        self.create_sqs_dlq()
        
        # 5. SNS 토픽 생성
        self.create_sns_topics()
        
        # 6. Bedrock Guardrail 생성
        self.create_bedrock_guardrail()
        
        # 7. Lambda 함수들 생성
        self.create_lambda_functions()
        
        # 8. API Gateway 생성
        self.create_api_gateway()
        
        # WebSocket API 설정
        self.create_websocket_api()
        
        # 9. CloudWatch 알람 생성
        self.create_cloudwatch_alarms()
        
        # 10. CDK 출력값 생성
        self.create_outputs()

    def create_cognito_user_pool(self):
        """Cognito 사용자 풀 생성"""
        # 사용자 풀 생성
        self.user_pool = cognito.UserPool(
            self, "ChatbotUserPool",
            user_pool_name="chatbot-users",
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                username=False
            ),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(
                    required=True,
                    mutable=True
                ),
                fullname=cognito.StandardAttribute(
                    required=False,
                    mutable=True
                )
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=False,
                require_uppercase=False,
                require_digits=True,
                require_symbols=True
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY
        )

        # 사용자 풀 클라이언트 생성
        self.user_pool_client = self.user_pool.add_client(
            "ChatbotWebClient",
            user_pool_client_name="chatbot-web-client",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True
            ),
            generate_secret=False,
            prevent_user_existence_errors=True,
            enable_token_revocation=True,
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30)
        )

        # 사용자 풀 도메인 생성 (선택사항 - Hosted UI를 사용할 경우)
        self.user_pool_domain = self.user_pool.add_domain(
            "ChatbotDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f"chatbot-{self.account}"
            )
        )

        # 관리자 그룹 생성
        self.admin_group = cognito.CfnUserPoolGroup(
            self, "AdminGroup",
            user_pool_id=self.user_pool.user_pool_id,
            group_name="admin",
            description="관리자 그룹",
            precedence=1  # 높은 우선순위
        )

    def create_s3_buckets(self):
        """S3 버킷들 생성 - 단순화됨"""
        # 프롬프트 저장용 버킷
        self.prompt_bucket = s3.Bucket(
            self, "PromptBucket",
            bucket_name=f"chatbot-prompts-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            cors=[
                s3.CorsRule(
                    allowed_headers=["*"],
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
                    allowed_origins=["*"],
                    max_age=3600
                )
            ]
        )

        # 기사 업로드용 버킷
        self.article_bucket = s3.Bucket(
            self, "ArticleBucket",
            bucket_name=f"chatbot-data-{self.account}-{self.region}",
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
            cors=[
                s3.CorsRule(
                    allowed_headers=["*"],
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.PUT, s3.HttpMethods.POST],
                    allowed_origins=["*"],
                    max_age=3600
                )
            ]
        )

    def create_dynamodb_tables(self):
        """DynamoDB 테이블 생성"""
        
        # =============================================================================
        # 새로 추가: 사용자 관리용 테이블들
        # =============================================================================
        
        # 1. 사용자 계정 테이블
        self.users_table = dynamodb.Table(
            self, "UsersTable",
            table_name="chatbot-users",
            partition_key=dynamodb.Attribute(
                name="user_id",  # Cognito User Sub
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            )
        )
        
        # 이메일로 사용자 검색을 위한 GSI
        self.users_table.add_global_secondary_index(
            index_name="email-index",
            partition_key=dynamodb.Attribute(
                name="email",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # 2. 사용량 관리 테이블
        self.usage_table = dynamodb.Table(
            self, "UsageTable",
            table_name="chatbot-usage",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="date",  # YYYY-MM-DD 형식
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"  # 데이터 자동 삭제를 위한 TTL
        )
        
        # 월별 사용량 집계를 위한 GSI
        self.usage_table.add_global_secondary_index(
            index_name="user_id-month-index",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="month",  # YYYY-MM 형식
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # 3. 구독 정보 테이블
        self.subscriptions_table = dynamodb.Table(
            self, "SubscriptionsTable",
            table_name="chatbot-subscriptions",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            )
        )
        
        # 구독 상태별 조회를 위한 GSI
        self.subscriptions_table.add_global_secondary_index(
            index_name="status-expiry_date-index",
            partition_key=dynamodb.Attribute(
                name="status",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="expiry_date",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        # =============================================================================
        # 기존 테이블들
        # =============================================================================
        


        # 프롬프트 메타데이터 테이블 (프로젝트 개념 제거)
        self.prompt_meta_table = dynamodb.Table(
            self, "PromptMetaTable",
            table_name="chatbot-prompts",
            partition_key=dynamodb.Attribute(
                name="user_id",  # 사용자 ID로 변경
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="promptId",  # UUID 기반 promptId
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # GSI: step_order 기반 정렬을 위한 인덱스 (사용자별)
        self.prompt_meta_table.add_global_secondary_index(
            index_name="user_id-stepOrder-index",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="stepOrder",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # 대화/생성 기록 테이블 (프로젝트 개념 제거)
        self.conversation_table = dynamodb.Table(
            self, "ConversationTable",
            table_name="chatbot-conversations",
            partition_key=dynamodb.Attribute(
                name="user_id",  # 사용자 ID로 변경
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="timestamp",
                type=dynamodb.AttributeType.NUMBER
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Step Functions 실행 결과 테이블
        self.execution_table = dynamodb.Table(
            self, "ExecutionTable",
            table_name="chatbot-executions",
            partition_key=dynamodb.Attribute(
                name="executionId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )

        # =============================================================================
        # Enhanced Agent System용 새로운 테이블들
        # =============================================================================
        
        # Perplexity API 검색 결과 캐싱 테이블
        self.perplexity_cache_table = dynamodb.Table(
            self, "PerplexityCacheTable",
            table_name="perplexity-search-cache",
            partition_key=dynamodb.Attribute(
                name="query_hash",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"  # 자동 캐시 만료
        )
        
        # 워크플로우 실행 메트릭 테이블
        self.execution_metrics_table = dynamodb.Table(
            self, "ExecutionMetricsTable",
            table_name="workflow-execution-metrics",
            partition_key=dynamodb.Attribute(
                name="execution_date",  # YYYY-MM-DD 형식
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="execution_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"  # 90일 후 자동 삭제
        )


    def create_sqs_dlq(self):
        """SQS DLQ 생성"""
        self.dlq = sqs.Queue(
            self, "IndexPromptDLQ",
            queue_name="chatbot-index-prompt-dlq",
            retention_period=Duration.days(14),
            visibility_timeout=Duration.minutes(5)
        )

        # 메인 큐 (S3 이벤트 재시도용)
        self.index_queue = sqs.Queue(
            self, "IndexPromptQueue", 
            queue_name="chatbot-index-prompt",
            visibility_timeout=Duration.minutes(5),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=self.dlq
            )
        )

    def create_sns_topics(self):
        """SNS 토픽 생성"""
        self.completion_topic = sns.Topic(
            self, "CompletionTopic",
            topic_name="chatbot-completion"
        )

        self.error_topic = sns.Topic(
            self, "ErrorTopic", 
            topic_name="chatbot-errors"
        )

    def create_bedrock_guardrail(self):
        """Bedrock Guardrail 생성 - 단순화됨"""
        
        # Agent용 IAM 역할 (OpenSearch 없이)
        self.agent_role = iam.Role(
            self, "BedrockAgentRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ]
        )
        
        # Knowledge Base용 IAM 역할 (OpenSearch 없이)
        self.kb_role = iam.Role(
            self, "BedrockKnowledgeBaseRole",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ]
        )
        
        self.kb_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                resources=[
                    self.prompt_bucket.bucket_arn,
                    f"{self.prompt_bucket.bucket_arn}/*"
                ]
            )
        )
        
        # Bedrock Agent 생성 (Knowledge Base 없이)
        self.bedrock_agent = bedrock.CfnAgent(
            self, "DynamicPromptAgent",
            agent_name=f"dynamic-prompt-agent-{int(time.time())}",
            description="동적 프롬프트 시스템 AI 어시스턴트",
            foundation_model="apac.anthropic.claude-3-sonnet-20240229-v1:0",
            agent_resource_role_arn=self.agent_role.role_arn,
            idle_session_ttl_in_seconds=1800,  # 30분
            instruction="당신은 동적 프롬프트 시스템의 AI 어시스턴트입니다. 사용자가 제공하는 프롬프트 카드의 내용에 따라 다양한 작업을 수행하며, 창의적이고 정확한 응답을 제공합니다. 항상 한국어로 응답하고, 사용자의 요청에 맞춰 유연하게 대응하세요."
        )
        
        # Agent Alias 생성 (배포용)
        self.agent_alias = bedrock.CfnAgentAlias(
            self, "DynamicPromptAgentAlias",
            agent_alias_name="production",
            agent_id=self.bedrock_agent.attr_agent_id,
            description="Production alias for Dynamic Prompt System agent"
        )

    def create_lambda_functions(self):
        """Lambda 함수들 생성 - 단순화됨"""
        # 공통 IAM 역할
        lambda_role = iam.Role(
            self, "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ]
        )

        # 필요한 리소스 권한만 추가
        lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "s3:GetObject",
                    "s3:PutObject", 
                    "s3:DeleteObject",
                    "s3:ListBucket",
                    "dynamodb:Query",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:GetItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Scan",
                    "dynamodb:GetRecords",
                    "dynamodb:GetShardIterator",
                    "dynamodb:DescribeStream",
                    "dynamodb:ListStreams",
                    "sqs:SendMessage",
                    "sqs:ReceiveMessage",
                    "sns:Publish",
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:Retrieve",
                    "bedrock:RetrieveAndGenerate",
                    "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminSetUserPassword",
                    "cognito-idp:AdminGetUser",
                    "cognito-idp:AdminDeleteUser",
                    "cognito-idp:AdminConfirmSignUp",
                    "cognito-idp:AdminInitiateAuth",
                    "cognito-idp:AdminRespondToAuthChallenge",
                    "cognito-idp:AdminListGroupsForUser",
                    "cognito-idp:AdminAddUserToGroup",
                    "cognito-idp:ConfirmForgotPassword",
                    "cognito-idp:ForgotPassword",
                    "cognito-idp:ConfirmSignUp",
                    "cognito-idp:ResendConfirmationCode"
                ],
                resources=[
                    self.prompt_bucket.bucket_arn,
                    self.prompt_bucket.bucket_arn + "/*",
                    self.article_bucket.bucket_arn,
                    self.article_bucket.bucket_arn + "/*",
                    "arn:aws:s3:::seoul-economic-news-data-2025",
                    "arn:aws:s3:::seoul-economic-news-data-2025/*",
                    # 기존 테이블들
                    self.prompt_meta_table.table_arn,
                    self.prompt_meta_table.table_arn + "/index/user_id-stepOrder-index",
                    self.conversation_table.table_arn,
                    self.execution_table.table_arn,
                    # 새로 추가된 사용자 관리 테이블들
                    self.users_table.table_arn,
                    self.users_table.table_arn + "/index/email-index",
                    self.usage_table.table_arn,
                    self.usage_table.table_arn + "/index/user_id-month-index",
                    self.subscriptions_table.table_arn,
                    self.subscriptions_table.table_arn + "/index/status-expiry_date-index",
                    # Prompt 메타 테이블
                    self.prompt_meta_table.table_arn,
                    self.prompt_meta_table.table_arn + "/index/user_id-stepOrder-index",
                    # Enhanced Agent System용 새로운 테이블들
                    self.perplexity_cache_table.table_arn,
                    self.execution_metrics_table.table_arn,
                    # SQS, SNS
                    self.dlq.queue_arn,
                    self.index_queue.queue_arn,
                    self.completion_topic.topic_arn,
                    self.error_topic.topic_arn,
                    # Cognito
                    self.user_pool.user_pool_arn,
                    f"arn:aws:cognito-idp:{self.region}:{self.account}:userpool/{self.user_pool.user_pool_id}"
                ]
            )
        )

        # 간단화된 뉴스 처리 시스템을 위한 Lambda Layer 생성
        self.news_processing_layer = lambda_.LayerVersion(
            self, "NewsProcessingLayer",
            code=lambda_.Code.from_asset("../lambda", 
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_11.bundling_image,
                    command=[
                        "bash", "-c",
                        "mkdir -p /asset-output/python && "
                        "cp -r /asset-input/date_intelligence /asset-output/python/ && "
                        "cp -r /asset-input/external_search /asset-output/python/ && "
                        "cp -r /asset-input/utils /asset-output/python/ && "
                        "pip install -r /asset-input/lambda_layers/langchain/requirements.txt -t /asset-output/python/ && "
                        "echo '서울경제신문 AI 요약 시스템 Layer 업데이트 완료 - 2025-07-28' && "
                        "ls -la /asset-output/python/"
                    ]
                )
            ),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_11],
            description="서울경제신문 AI 요약 시스템 - 간단화된 7단계 플로우 처리"
        )

        # 1. Lambda (핵심 기능) - 간단화된 뉴스 처리 시스템 적용
        self.generate_lambda = lambda_.Function(
            self, "GenerateFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="generate.lambda_handler",  # 수정된 핸들러 이름
            code=lambda_.Code.from_asset("../lambda/generate"),
            timeout=Duration.minutes(15),
            memory_size=3008,
            role=lambda_role,
            layers=[self.news_processing_layer],  # 수정된 Layer 이름
            environment={
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "EXECUTION_TABLE": self.execution_table.table_name,
                "KNOWLEDGE_BASE_ID": "PGQV3JXPET",
                "OPENSEARCH_COLLECTION_ID": "i56h0ibud5e0sd0hz7ch",
                "S3_BUCKET_NAME": "seoul-economic-news-data-2025",
                "S3_DATA_PREFIX": "news-data-md/",
                "NEWS_BUCKET": "seoul-economic-news-data-2025",
                "PERPLEXITY_API_KEY": "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",
                "PERPLEXITY_CACHE_TABLE": "perplexity-search-cache",
                "EXECUTION_METRICS_TABLE": "workflow-execution-metrics",
                "REGION": self.region,
            },
            dead_letter_queue=self.dlq
        )
        
        # 🔥 Lambda Response Streaming - 일단 주석 처리 (CloudFormation 미지원)
        # cfn_generate_function = self.generate_lambda.node.default_child
        # cfn_generate_function.add_property_override("InvokeConfig", {
        #     "InvokeMode": "RESPONSE_STREAM"
        # })

        # 2. 프롬프트 저장 기능은 generate Lambda에서 통합 처리
        # (별도 Lambda 함수 불필요 - 간단화됨)
        self.save_prompt_lambda = self.generate_lambda  # generate Lambda가 프롬프트도 처리

        # 3. 인증 관리 Lambda
        self.auth_lambda = lambda_.Function(
            self, "AuthFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="auth.handler",
            code=lambda_.Code.from_asset("../lambda/auth"),
            timeout=Duration.minutes(1),
            memory_size=256,
            role=lambda_role,
            environment={
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": self.user_pool_client.user_pool_client_id,
                "REGION": self.region,
                "LOG_LEVEL": "INFO",
            }
        )

        # 4. 사용자 관리 Lambda (개선된 버전)
        self.user_management_lambda = lambda_.Function(
            self, "UserManagementFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="user_management.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/user_management"),
            timeout=Duration.minutes(2),
            memory_size=512,
            role=lambda_role,
            environment={
                "USERS_TABLE_NAME": self.users_table.table_name,
                "USAGE_TABLE_NAME": self.usage_table.table_name,
                "SUBSCRIPTIONS_TABLE_NAME": self.subscriptions_table.table_name,
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "LOG_LEVEL": "INFO",
            }
        )

        # 5. JWT Authorizer Lambda (새로 추가)
        self.jwt_authorizer_lambda = lambda_.Function(
            self, "JWTAuthorizerFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="authorizer.handler",
            code=lambda_.Code.from_asset("../lambda/authorizer"),
            timeout=Duration.minutes(1),
            memory_size=256,
            role=lambda_role,
            environment={
                "USER_POOL_ID": self.user_pool.user_pool_id,
                "USER_POOL_CLIENT_ID": self.user_pool_client.user_pool_client_id,
                "REGION": self.region,
                "LOG_LEVEL": "INFO",
            }
        )


    # 간소화된 CORS 설정 함수
    def _create_cors_options_method(self, resource, allowed_methods):
        """CORS OPTIONS 메소드 생성 (간소화)"""
        return resource.add_method(
            "OPTIONS",
            apigateway.MockIntegration(
                integration_responses=[{
                    'statusCode': '200',
                    'responseParameters': {
                        'method.response.header.Access-Control-Allow-Headers': "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'",
                        'method.response.header.Access-Control-Allow-Origin': "'*'",
                        'method.response.header.Access-Control-Allow-Methods': f"'{allowed_methods}'"
                    }
                }],
                request_templates={
                    'application/json': '{"statusCode": 200}'
                }
            ),
            method_responses=[{
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Headers': True,
                    'method.response.header.Access-Control-Allow-Origin': True,
                    'method.response.header.Access-Control-Allow-Methods': True
                }
            }],
            authorization_type=apigateway.AuthorizationType.NONE
        )

    def create_api_gateway(self):
        """API Gateway 생성 - 간소화된 버전"""
        # REST API 생성
        self.api = apigateway.RestApi(
            self, "ChatbotApi",
            rest_api_name="chatbot-api",
            description="동적 프롬프트 시스템 - 완전한 빈깡통 AI",
            retain_deployments=True
        )

        # JWT Lambda Authorizer 생성
        self.api_authorizer = apigateway.RequestAuthorizer(
            self, "ChatbotApiAuthorizer",
            handler=self.jwt_authorizer_lambda,
            identity_sources=[apigateway.IdentitySource.header('Authorization')],
            authorizer_name="chatbot-jwt-authorizer",
            results_cache_ttl=Duration.seconds(300)  # 5분 캐시
        )

        # 인증 관련 경로 생성
        self.create_auth_routes()
        
        # 사용자 관리 경로 생성
        self.create_user_routes()
        
        # 프롬프트 관리 경로 생성
        self.create_prompt_routes()
        
        # 생성 관련 경로 생성 (프로젝트 개념 제거)
        self.create_generate_routes()

    def create_auth_routes(self):
        """인증 관련 API 경로 생성"""
        auth_resource = self.api.root.add_resource("auth")
        
        # 인증 엔드포인트들
        auth_endpoints = ["signup", "signin", "refresh", "signout", "verify", "forgot-password", "confirm-password", "init-admin"]
        
        for endpoint in auth_endpoints:
            endpoint_resource = auth_resource.add_resource(endpoint)
            
            # POST 메소드 추가
            endpoint_resource.add_method(
                "POST",
                apigateway.LambdaIntegration(self.auth_lambda, proxy=True),
                authorization_type=apigateway.AuthorizationType.NONE
            )
            
            # CORS 옵션 추가
            self._create_cors_options_method(endpoint_resource, "POST,OPTIONS")

    def create_user_routes(self):
        """사용자 관리 관련 API 경로 생성"""
        user_resource = self.api.root.add_resource("user")
        
        # GET /user/profile (사용자 프로필 조회)
        profile_resource = user_resource.add_resource("profile")
        profile_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.user_management_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # PUT /user/profile (사용자 프로필 수정)
        profile_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.user_management_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(profile_resource, "GET,PUT,OPTIONS")
        
        # GET /user/usage (사용량 조회)
        usage_resource = user_resource.add_resource("usage")
        usage_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.user_management_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(usage_resource, "GET,OPTIONS")
        
        # GET /user/subscription (구독 정보 조회)
        subscription_resource = user_resource.add_resource("subscription")
        subscription_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.user_management_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # PUT /user/subscription (구독 정보 수정)
        subscription_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.user_management_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(subscription_resource, "GET,PUT,OPTIONS")

    def create_prompt_routes(self):
        """프롬프트 관리 API 경로 생성 - 사용자별 관리로 변경"""
        prompts_resource = self.api.root.add_resource("prompts")
        
        # POST /prompts (새 프롬프트 카드 생성)
        prompts_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.generate_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # GET /prompts (프롬프트 카드 목록 조회)
        prompts_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.generate_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(prompts_resource, "GET,POST,PUT,DELETE,OPTIONS")
        
        # /prompts/{promptId} 리소스
        prompt_card_resource = prompts_resource.add_resource("{promptId}")
        
        # PUT /prompts/{promptId} (프롬프트 카드 수정)
        prompt_card_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.generate_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # DELETE /prompts/{promptId} (프롬프트 카드 삭제)
        prompt_card_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.generate_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(prompt_card_resource, "GET,POST,PUT,DELETE,OPTIONS")
        
        # /prompts/{promptId}/content 리소스 추가
        content_resource = prompt_card_resource.add_resource("content")
        
        # GET /prompts/{promptId}/content (프롬프트 내용 조회)
        content_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.generate_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(content_resource, "GET,OPTIONS")

    # Step Functions 제거됨 - 단순화된 동적 프롬프트 시스템으로 불필요
    # def create_step_functions(self):
    #     """Step Functions 스테이트 머신 생성 - 제거됨"""
    #     pass

    def create_cloudwatch_alarms(self):
        """CloudWatch 알람 생성"""
        # Lambda 함수 오류율 알람
        lambda_funcs = [
            (self.generate_lambda, "Generate"),
            (self.auth_lambda, "Auth")
        ]
        
        for lambda_func, alarm_name in lambda_funcs:
            cloudwatch.Alarm(
                self, f"{alarm_name}ErrorAlarm",
                metric=lambda_func.metric_errors(period=Duration.minutes(5)),
                threshold=3,
                evaluation_periods=2,
                alarm_description=f"{alarm_name} Lambda 함수 오류율이 높습니다"
            )

        # DLQ 메시지 알람
        cloudwatch.Alarm(
            self, "DLQMessageAlarm",
            metric=self.dlq.metric("ApproximateNumberOfVisibleMessages"),
            threshold=1,
            evaluation_periods=1,
            alarm_description="DLQ에 메시지가 있습니다"
        )

    def create_budget_alarms(self):
        """비용 알람 생성 - 권한 문제로 임시 비활성화"""
        pass
        # 월 $1000 예산 알람
        # budgets.CfnBudget(
        #     self, "MonthlyBudget",
        #     budget=budgets.CfnBudget.BudgetDataProperty(
        #         budget_name="title-generator-monthly-budget",
        #         budget_type="COST",
        #         budget_limit=budgets.CfnBudget.SpendProperty(
        #             amount=1000,
        #             unit="USD"
        #         ),
        #         time_unit="MONTHLY",
        #         cost_filters={
        #             "Service": ["Amazon Bedrock", "AWS Lambda"]  # 🔧 수정: OpenSearch 제거
        #         }
        #     ),
        #     notifications_with_subscribers=[
        #         budgets.CfnBudget.NotificationWithSubscribersProperty(
        #             notification=budgets.CfnBudget.NotificationProperty(
        #                 notification_type="ACTUAL",
        #                 comparison_operator="GREATER_THAN",
        #                 threshold=80
        #             ),
        #             subscribers=[
        #                 # 🔧 수정: 더미 이메일 제거 - 실제 사용 시 환경변수나 파라미터로 설정
        #                 # budgets.CfnBudget.SubscriberProperty(
        #                 #     subscription_type="EMAIL",
        #                 #     address="admin@example.com"
        #                 # )
        #             ]
        #         )
        #     ]
        # )

    def create_outputs(self):
        """CDK 출력값 생성"""
        # 중요: API Gateway 출력
        CfnOutput(
            self, "ApiGatewayUrl",
            value=self.api.url,
            description="API Gateway URL",
            export_name="ChatbotApiUrl"
        )

        CfnOutput(
            self, "PromptBucketName",
            value=self.prompt_bucket.bucket_name,
            description="프롬프트 S3 버킷 이름",
            export_name="ChatbotPromptBucketName"
        )

        # 🔧 추가: 중요한 리소스 출력값들 추가
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID",
            export_name="ChatbotUserPoolId"
        )

        CfnOutput(
            self, "UserPoolClientId", 
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
            export_name="ChatbotUserPoolClientId"
        )

    def create_websocket_api(self):
        """WebSocket API 생성 - 실시간 스트리밍용"""
        
        # WebSocket 연결 테이블
        self.websocket_connections_table = dynamodb.Table(
            self, "WebSocketConnectionsTable",
            table_name="chatbot-websocket-connections",
            partition_key=dynamodb.Attribute(
                name="connectionId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )
        
        # WebSocket Lambda 함수들용 공통 역할
        websocket_lambda_role = iam.Role(
            self, "WebSocketLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonBedrockFullAccess")
            ]
        )
        
        # WebSocket 및 DynamoDB 권한 추가
        websocket_lambda_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "execute-api:ManageConnections",
                    "dynamodb:PutItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:BatchWriteItem",
                    "dynamodb:UpdateItem",
                    "s3:GetObject",
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream",
                    "bedrock:Retrieve",
                    "bedrock-agent:Retrieve"
                ],
                resources=[
                    f"arn:aws:execute-api:{self.region}:{self.account}:*/*/*",
                    self.websocket_connections_table.table_arn,
                    self.prompt_meta_table.table_arn,
                    self.prompt_bucket.bucket_arn + "/*",
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/Conversations",
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/Messages",
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/ChatbotConversations",
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/ChatbotMessages",
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/perplexity-search-cache",  # Enhanced Agent System용
                    f"arn:aws:bedrock:{self.region}::foundation-model/*"
                ]
            )
        )
        
        # Connect Lambda
        self.websocket_connect_lambda = lambda_.Function(
            self, "WebSocketConnectFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="connect.handler",
            code=lambda_.Code.from_asset("../lambda/websocket"),
            timeout=Duration.minutes(1),
            memory_size=256,
            role=websocket_lambda_role,
            environment={
                "CONNECTIONS_TABLE": self.websocket_connections_table.table_name,
                "REGION": self.region
            }
        )
        
        # Disconnect Lambda
        self.websocket_disconnect_lambda = lambda_.Function(
            self, "WebSocketDisconnectFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="disconnect.handler",
            code=lambda_.Code.from_asset("../lambda/websocket"),
            timeout=Duration.minutes(1),
            memory_size=256,
            role=websocket_lambda_role,
            environment={
                "CONNECTIONS_TABLE": self.websocket_connections_table.table_name,
                "REGION": self.region
            }
        )
        
        # WebSocket API 먼저 생성
        self.websocket_api = apigatewayv2.WebSocketApi(
            self, "ChatbotWebSocketApi",
            api_name="chatbot-websocket-api",
            description="실시간 스트리밍을 위한 WebSocket API"
        )

        # Stream Lambda (WebSocket API 도메인 정보 포함)
        self.websocket_stream_lambda = lambda_.Function(
            self, "WebSocketStreamFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="stream.handler",
            code=lambda_.Code.from_asset("../lambda/websocket"),
            timeout=Duration.minutes(15),
            memory_size=3008,
            role=websocket_lambda_role,
            layers=[self.news_processing_layer],  # Enhanced Agent System Layer 추가
            environment={
                "CONNECTIONS_TABLE": self.websocket_connections_table.table_name,
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region,
                "CONVERSATIONS_TABLE": "ChatbotConversations",
                "MESSAGES_TABLE": "ChatbotMessages",
                "PERPLEXITY_API_KEY": "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",  # 업데이트된 테스트 키
                "API_GATEWAY_DOMAIN": self.websocket_api.api_endpoint.replace("wss://", "").replace("ws://", ""),
                "STAGE": "prod",
                "KNOWLEDGE_BASE_ID": "PGQV3JXPET",
                "S3_BUCKET_NAME": "seoul-economic-news-data-2025",
                "NEWS_BUCKET": "seoul-economic-news-data-2025"
            }
        )
        
        # WebSocket API 라우팅 설정 (이미 생성된 API에 라우트 추가)
        self.websocket_api.add_route(
            "$connect",
            integration=integrations.WebSocketLambdaIntegration(
                "ConnectIntegration",
                self.websocket_connect_lambda
            )
        )
        
        self.websocket_api.add_route(
            "$disconnect",
            integration=integrations.WebSocketLambdaIntegration(
                "DisconnectIntegration",
                self.websocket_disconnect_lambda
            )
        )
        
        # Stream 라우트 추가
        self.websocket_api.add_route(
            "stream",
            integration=integrations.WebSocketLambdaIntegration(
                "StreamIntegration",
                self.websocket_stream_lambda
            )
        )
        
        # WebSocket API Stage 생성
        self.websocket_stage = apigatewayv2.WebSocketStage(
            self, "WebSocketStage",
            web_socket_api=self.websocket_api,
            stage_name="prod",
            auto_deploy=True
        )
        
        # WebSocket API URL 출력 (stage 포함)
        websocket_url = f"{self.websocket_api.api_endpoint}/prod"
        CfnOutput(
            self, "WebSocketApiUrl",
            value=websocket_url,
            description="WebSocket API URL with stage",
            export_name="ChatbotWebSocketApiUrl"
        )

    def create_generate_routes(self):
        """생성 관련 API 경로 생성 - 프로젝트 개념 제거"""
        generate_resource = self.api.root.add_resource("generate")
        
        # POST /generate (일반 생성)
        generate_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.generate_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(generate_resource, "POST,OPTIONS")
        
        # /generate/stream 리소스 (스트리밍)
        stream_resource = generate_resource.add_resource("stream")
        
        # 스트리밍 메서드 추가
        stream_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.generate_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(stream_resource, "OPTIONS,POST")

    # def create_crew_routes(self):
    #     """CrewAI 관련 API 경로 생성 - 기능 제거됨"""
    #     pass 
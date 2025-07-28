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

class SeoulEconomicNewsStack(Stack):
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
        
        # 10. 비용 알람 생성
        # self.create_budget_alarms()  # 권한 문제로 임시 비활성화
        
        # 11. CDK 출력값 생성
        self.create_outputs()

    def create_cognito_user_pool(self):
        """Cognito 사용자 풀 생성"""
        # 사용자 풀 생성
        self.user_pool = cognito.UserPool(
            self, "SeoulEconomicNewsUserPool",
            user_pool_name="title-generator-users",
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
            "SeoulEconomicNewsWebClient",
            user_pool_client_name="title-generator-web-client",
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
            "SeoulEconomicNewsDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f"title-generator-{self.account}"
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
            bucket_name=f"title-generator-prompts-{self.account}-{self.region}",
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
            bucket_name=f"title-generator-articles-{self.account}-{self.region}",
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
            table_name="title-generator-users",
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
            table_name="title-generator-usage",
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
            table_name="title-generator-subscriptions",
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
        
        # 프로젝트 메타데이터 테이블
        self.project_table = dynamodb.Table(
            self, "ProjectTable",
            table_name="title-generator-projects-auth",
            partition_key=dynamodb.Attribute(
                name="projectId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            )
        )

        # 프롬프트 메타데이터 테이블 (확장)
        self.prompt_meta_table = dynamodb.Table(
            self, "PromptMetaTable",
            table_name="title-generator-prompt-meta-v2-auth",
            partition_key=dynamodb.Attribute(
                name="projectId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="promptId",  # UUID 기반 promptId로 변경
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )
        
        # GSI: step_order 기반 정렬을 위한 인덱스
        self.prompt_meta_table.add_global_secondary_index(
            index_name="projectId-stepOrder-index",
            partition_key=dynamodb.Attribute(
                name="projectId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="stepOrder",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # 대화/생성 기록 테이블
        self.conversation_table = dynamodb.Table(
            self, "ConversationTable",
            table_name="title-generator-conversations-auth",
            partition_key=dynamodb.Attribute(
                name="projectId",
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
            table_name="title-generator-executions-auth",
            partition_key=dynamodb.Attribute(
                name="executionId",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl"
        )

        # =============================================================================
        # CrewAI 구조를 위한 새로운 테이블들
        # =============================================================================

        # 프롬프트 인스턴스 테이블 (사용자가 입력한 placeholder 값들)
        self.prompt_instance_table = dynamodb.Table(
            self, "PromptInstanceTable",
            table_name="title-generator-prompt-instances-auth",
            partition_key=dynamodb.Attribute(
                name="projectId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="instanceId",  # UUID 기반
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES  # DynamoDB Streams 활성화
        )

        # 사용자별 인스턴스 조회를 위한 GSI
        self.prompt_instance_table.add_global_secondary_index(
            index_name="userId-created-index",
            partition_key=dynamodb.Attribute(
                name="userId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="createdAt",
                type=dynamodb.AttributeType.STRING
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # CrewAI 설정 저장 테이블
        self.crew_config_table = dynamodb.Table(
            self, "CrewConfigTable",
            table_name="title-generator-crew-configs-auth",
            partition_key=dynamodb.Attribute(
                name="configId",  # projectId 기반 생성
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery_specification=dynamodb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=True
            )
        )

        # 프로젝트별 조회를 위한 GSI
        self.crew_config_table.add_global_secondary_index(
            index_name="projectId-version-index",
            partition_key=dynamodb.Attribute(
                name="projectId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="version",
                type=dynamodb.AttributeType.NUMBER
            ),
            projection_type=dynamodb.ProjectionType.ALL
        )

    def create_sqs_dlq(self):
        """SQS DLQ 생성"""
        self.dlq = sqs.Queue(
            self, "IndexPromptDLQ",
            queue_name="title-generator-index-prompt-dlq-auth",
            retention_period=Duration.days(14),
            visibility_timeout=Duration.minutes(5)
        )

        # 메인 큐 (S3 이벤트 재시도용)
        self.index_queue = sqs.Queue(
            self, "IndexPromptQueue", 
            queue_name="title-generator-index-prompt-auth",
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
            topic_name="title-generator-completion-auth"
        )

        self.error_topic = sns.Topic(
            self, "ErrorTopic", 
            topic_name="title-generator-errors-auth"
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
            foundation_model="anthropic.claude-3-sonnet-20240229-v1:0",
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
                    self.project_table.table_arn,
                    self.prompt_meta_table.table_arn,
                    self.prompt_meta_table.table_arn + "/index/projectId-stepOrder-index",
                    self.conversation_table.table_arn,
                    self.execution_table.table_arn,
                    # 새로 추가된 사용자 관리 테이블들
                    self.users_table.table_arn,
                    self.users_table.table_arn + "/index/email-index",
                    self.usage_table.table_arn,
                    self.usage_table.table_arn + "/index/user_id-month-index",
                    self.subscriptions_table.table_arn,
                    self.subscriptions_table.table_arn + "/index/status-expiry_date-index",
                    # CrewAI 구조를 위한 새로운 테이블들
                    self.prompt_instance_table.table_arn,
                    self.prompt_instance_table.table_arn + "/index/userId-created-index",
                    self.crew_config_table.table_arn,
                    self.crew_config_table.table_arn + "/index/projectId-version-index",
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

        # 1. 제목 생성 Lambda (핵심 기능) - 최대 성능 설정 + 스트리밍 활성화
        self.generate_lambda = lambda_.Function(
            self, "GenerateFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="generate.handler",
            # 🔧 강제 재배포를 위해 코드 자산을 명시적으로 지정
            code=lambda_.Code.from_asset("../lambda/generate"),
            timeout=Duration.minutes(15),
            memory_size=3008,
            role=lambda_role,
            environment={
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "EXECUTION_TABLE": self.execution_table.table_name,
                "KNOWLEDGE_BASE_ID": "PGQV3JXPET",
                "OPENSEARCH_COLLECTION_ID": "i56h0ibud5e0sd0hz7ch",
                "S3_BUCKET_NAME": "seoul-economic-news-data-2025",
                "S3_DATA_PREFIX": "news-data-md/",
                "REGION": self.region,
            },
            dead_letter_queue=self.dlq
        )
        
        # 🔥 Lambda Response Streaming - 일단 주석 처리 (CloudFormation 미지원)
        # cfn_generate_function = self.generate_lambda.node.default_child
        # cfn_generate_function.add_property_override("InvokeConfig", {
        #     "InvokeMode": "RESPONSE_STREAM"
        # })

        # 2. 프롬프트 저장 Lambda (단순화됨)
        self.save_prompt_lambda = lambda_.Function(
            self, "SavePromptFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="save_prompt.handler",
            code=lambda_.Code.from_asset("../lambda/save_prompt"),
            timeout=Duration.minutes(2),
            memory_size=512,
            role=lambda_role,
            environment={
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region,
            }
        )

        # 3. 프로젝트 관리 Lambda
        self.project_lambda = lambda_.Function(
            self, "ProjectFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="project.handler",
            code=lambda_.Code.from_asset("../lambda/project"),
            timeout=Duration.minutes(1),
            memory_size=256,
            role=lambda_role,
            environment={
                "PROJECT_TABLE": self.project_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region,
            }
        )

        # 4. 인증 관리 Lambda
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
                "USERS_TABLE": self.users_table.table_name,
                "USAGE_TABLE": self.usage_table.table_name,
                "SUBSCRIPTIONS_TABLE": self.subscriptions_table.table_name,
                "REGION": self.region,
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

        # 6. 사용자 관리 Lambda (개선된 버전)
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

        # =============================================================================
        # CrewAI 구조를 위한 새로운 Lambda 함수들
        # =============================================================================

        # 7. CrewAI 설정 빌더 Lambda (DynamoDB Streams 트리거)
        self.crew_builder_lambda = lambda_.Function(
            self, "CrewBuilderFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="crew_builder.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/crew_builder"),
            timeout=Duration.minutes(5),
            memory_size=1024,
            role=lambda_role,
            environment={
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_INSTANCE_TABLE": self.prompt_instance_table.table_name,
                "CREW_CONFIG_TABLE": self.crew_config_table.table_name,
                "CREW_CONFIG_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region,
                "LOG_LEVEL": "INFO",
            }
        )

        # 8. CrewAI 플래너 Lambda (실제 AI 작업 수행)
        self.planner_lambda = lambda_.Function(
            self, "PlannerFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="planner.lambda_handler",
            code=lambda_.Code.from_asset("../lambda/planner"),
            timeout=Duration.minutes(10),
            memory_size=2048,
            role=lambda_role,
            environment={
                "CREW_CONFIG_BUCKET": self.prompt_bucket.bucket_name,
                "CREW_CONFIG_TABLE": self.crew_config_table.table_name,
                "CONVERSATION_TABLE": self.conversation_table.table_name,
                "BEDROCK_MODEL_ID": "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "KNOWLEDGE_BASE_ID": "PGQV3JXPET",
                "OPENSEARCH_COLLECTION_ID": "i56h0ibud5e0sd0hz7ch",
                "S3_BUCKET_NAME": "seoul-economic-news-data-2025",
                "S3_DATA_PREFIX": "news-data-md/",
                "REGION": self.region,
                "LOG_LEVEL": "INFO",
            }
        )

        # DynamoDB Streams 이벤트 소스 매핑
        # prompt_instance_table의 변경사항을 crew_builder_lambda가 감지하도록 설정
        self.prompt_instance_table.grant_stream_read(self.crew_builder_lambda)
        lambda_.EventSourceMapping(
            self, "PromptInstanceStreamMapping",
            target=self.crew_builder_lambda,
            event_source_arn=self.prompt_instance_table.table_stream_arn,
            starting_position=lambda_.StartingPosition.TRIM_HORIZON,
            batch_size=5,
            max_batching_window=Duration.seconds(30),
            retry_attempts=3
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
            self, "SeoulEconomicNewsApi",
            rest_api_name="title-generator-api",
            description="동적 프롬프트 시스템 - 완전한 빈깡통 AI",
            retain_deployments=True
        )

        # JWT Lambda Authorizer 생성
        self.api_authorizer = apigateway.RequestAuthorizer(
            self, "SeoulEconomicNewsApiAuthorizer",
            handler=self.jwt_authorizer_lambda,
            identity_sources=[apigateway.IdentitySource.header('Authorization')],
            authorizer_name="title-generator-jwt-authorizer",
            results_cache_ttl=Duration.seconds(300)  # 5분 캐시
        )

        # 인증 관련 경로 생성
        self.create_auth_routes()
        
        # 사용자 관리 경로 생성
        self.create_user_routes()
        
        # 프로젝트 관련 경로 생성
        self.create_project_routes()
        
        # 프롬프트 관리 경로 생성
        self.create_prompt_routes()
        
        # CrewAI 관련 경로 생성
        self.create_crew_routes()
        
        # 스트리밍 엔드포인트 추가
        projects_resource = self.api.root.get_resource("projects")
        project_resource = projects_resource.get_resource("{projectId}")
        
        # 스트리밍 리소스 생성
        generate_resource = project_resource.get_resource("generate")
        stream_resource = generate_resource.add_resource("stream")
        
        # 스트리밍 메서드 추가 (간소화된 설정)
        stream_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.generate_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(stream_resource, "OPTIONS,POST")

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

    def create_project_routes(self):
        """프로젝트 관련 API 경로 생성"""
        projects_resource = self.api.root.add_resource("projects")
        
        # POST /projects (프로젝트 생성)
        projects_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.project_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )

        # GET /projects (프로젝트 목록)
        projects_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.project_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(projects_resource, "GET,POST,PUT,DELETE,OPTIONS")

        # /projects/{id} 리소스
        project_resource = projects_resource.add_resource("{projectId}")
        
        # GET /projects/{id} (프로젝트 상세)
        project_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.project_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # PUT /projects/{id} (프로젝트 수정)
        project_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.project_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # DELETE /projects/{id} (프로젝트 삭제)
        project_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.project_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(project_resource, "GET,POST,PUT,DELETE,OPTIONS")

        # POST /projects/{id}/generate (제목 생성)
        generate_resource = project_resource.add_resource("generate")
        generate_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.generate_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(generate_resource, "POST,OPTIONS")

        # GET /projects/{id}/upload-url (파일 업로드용 pre-signed URL)
        upload_url_resource = project_resource.add_resource("upload-url")
        upload_url_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.project_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(upload_url_resource, "GET,OPTIONS")

    def create_prompt_routes(self):
        """프롬프트 관리 API 경로 생성"""
        prompts_resource = self.api.root.add_resource("prompts")
        prompts_project_resource = prompts_resource.add_resource("{projectId}")
        
        # POST /prompts/{projectId} (새 프롬프트 카드 생성)
        prompts_project_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # GET /prompts/{projectId} (프롬프트 카드 목록 조회)
        prompts_project_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(prompts_project_resource, "GET,POST,PUT,DELETE,OPTIONS")
        
        # /prompts/{projectId}/{promptId} 리소스
        prompt_card_resource = prompts_project_resource.add_resource("{promptId}")
        
        # PUT /prompts/{projectId}/{promptId} (프롬프트 카드 수정)
        prompt_card_resource.add_method(
            "PUT",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # DELETE /prompts/{projectId}/{promptId} (프롬프트 카드 삭제)
        prompt_card_resource.add_method(
            "DELETE",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.NONE
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(prompt_card_resource, "GET,POST,PUT,DELETE,OPTIONS")
        
        # /prompts/{projectId}/{promptId}/content 리소스 추가
        content_resource = prompt_card_resource.add_resource("content")
        
        # GET /prompts/{projectId}/{promptId}/content (프롬프트 내용 조회)
        content_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
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
            (self.project_lambda, "Project"),
            (self.save_prompt_lambda, "SavePrompt"),
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
            export_name="NewsSummarizerApiUrl"
        )

        CfnOutput(
            self, "PromptBucketName",
            value=self.prompt_bucket.bucket_name,
            description="프롬프트 S3 버킷 이름",
            export_name="NewsSummarizerPromptBucketName"
        )

        # 🔧 추가: 중요한 리소스 출력값들 추가
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID",
            export_name="NewsSummarizerUserPoolId"
        )

        CfnOutput(
            self, "UserPoolClientId", 
            value=self.user_pool_client.user_pool_client_id,
            description="Cognito User Pool Client ID",
            export_name="NewsSummarizerUserPoolClientId"
        )

    def create_websocket_api(self):
        """WebSocket API 생성 - 실시간 스트리밍용"""
        
        # WebSocket 연결 테이블
        self.websocket_connections_table = dynamodb.Table(
            self, "WebSocketConnectionsTable",
            table_name="title-generator-websocket-connections",
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
                    "s3:GetObject",
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=[
                    f"arn:aws:execute-api:{self.region}:{self.account}:*/*/*",
                    self.websocket_connections_table.table_arn,
                    self.prompt_meta_table.table_arn,
                    self.prompt_bucket.bucket_arn + "/*",
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/Conversations",
                    f"arn:aws:dynamodb:{self.region}:{self.account}:table/Messages"
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
        
        # Stream Lambda
        self.websocket_stream_lambda = lambda_.Function(
            self, "WebSocketStreamFunction",
            runtime=lambda_.Runtime.PYTHON_3_11,
            handler="stream.handler",
            code=lambda_.Code.from_asset("../lambda/websocket"),
            timeout=Duration.minutes(15),
            memory_size=3008,
            role=websocket_lambda_role,
            environment={
                "CONNECTIONS_TABLE": self.websocket_connections_table.table_name,
                "PROMPT_META_TABLE": self.prompt_meta_table.table_name,
                "PROMPT_BUCKET": self.prompt_bucket.bucket_name,
                "REGION": self.region,
                "CONVERSATIONS_TABLE": "Conversations",
                "MESSAGES_TABLE": "Messages"
            }
        )
        
        # WebSocket API 생성
        self.websocket_api = apigatewayv2.WebSocketApi(
            self, "SeoulEconomicNewsWebSocketApi",
            api_name="title-generator-websocket-api",
            description="실시간 스트리밍을 위한 WebSocket API",
            connect_route_options=apigatewayv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "ConnectIntegration",
                    self.websocket_connect_lambda
                )
            ),
            disconnect_route_options=apigatewayv2.WebSocketRouteOptions(
                integration=integrations.WebSocketLambdaIntegration(
                    "DisconnectIntegration", 
                    self.websocket_disconnect_lambda
                )
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
            export_name="NewsSummarizerWebSocketApiUrl"
        )

    def create_crew_routes(self):
        """CrewAI 관련 API 경로 생성"""
        crew_resource = self.api.root.add_resource("crew")
        
        # POST /crew/execute (CrewAI 워크플로우 실행)
        execute_resource = crew_resource.add_resource("execute")
        execute_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.planner_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(execute_resource, "POST,OPTIONS")
        
        # GET /crew/config/{projectId} (CrewAI 설정 조회)
        config_resource = crew_resource.add_resource("config")
        project_config_resource = config_resource.add_resource("{projectId}")
        project_config_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.crew_builder_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(project_config_resource, "GET,OPTIONS")
        
        # POST /crew/instances (프롬프트 인스턴스 생성)
        instances_resource = crew_resource.add_resource("instances")
        instances_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # GET /crew/instances/{projectId} (프로젝트의 인스턴스 목록)
        project_instances_resource = instances_resource.add_resource("{projectId}")
        project_instances_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(self.save_prompt_lambda, proxy=True),
            authorization_type=apigateway.AuthorizationType.CUSTOM,
            authorizer=self.api_authorizer
        )
        
        # CORS 옵션 추가
        self._create_cors_options_method(instances_resource, "GET,POST,OPTIONS")
        self._create_cors_options_method(project_instances_resource, "GET,OPTIONS") 
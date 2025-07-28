// AWS Amplify v6 설정 - 새 Chatbot 프로젝트
export const config = {
  // API Gateway 설정
  apiGateway: {
    REGION: "ap-northeast-2",
    URL: "https://7dx6a5fjma.execute-api.ap-northeast-2.amazonaws.com/prod",
  },

  // Cognito 설정
  cognito: {
    REGION: "ap-northeast-2",
    USER_POOL_ID: "ap-northeast-2_rjkGlSgbj",
    APP_CLIENT_ID: "153t9o7vjiib427jjc7ofadbg",
  },

  // WebSocket 설정
  webSocket: {
    URL: "wss://xx57ijwpk7.execute-api.ap-northeast-2.amazonaws.com/prod",
  },
};

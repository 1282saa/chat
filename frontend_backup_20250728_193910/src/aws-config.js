// AWS Amplify v6 설정 - 새 Chatbot 프로젝트
export const config = {
  // API Gateway 설정
  apiGateway: {
    REGION: "ap-northeast-2",
    URL: "https://5navjh90o6.execute-api.ap-northeast-2.amazonaws.com/prod",
  },

  // Cognito 설정
  cognito: {
    REGION: "ap-northeast-2",
    USER_POOL_ID: "ap-northeast-2_pznD73Cop",
    APP_CLIENT_ID: "1agd035rfvk8jq8cki6e4nvfes",
  },

  // WebSocket 설정
  webSocket: {
    URL: "wss://6iujb0ea76.execute-api.ap-northeast-2.amazonaws.com/prod",
  },
};

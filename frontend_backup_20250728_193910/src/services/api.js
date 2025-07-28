import axios from "axios";
import { config } from "../aws-config";

// API 기본 설정 - 새로운 배포된 API Gateway URL 사용
const API_BASE_URL = config.apiGateway.URL;

// Mock data for development
const mockUsageData = {
  todayRequests: 127,
  todayTokens: 45320,
  monthlyLimit: 1000000,
  monthlyUsed: 523400,
  plan: {
    name: "Professional",
    expiresAt: "2025-02-28",
    features: ["월 100만 토큰", "우선 지원", "API 액세스"],
  },
  chartData: Array.from({ length: 30 }, (_, i) => ({
    date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000)
      .toISOString()
      .split("T")[0],
    tokens: Math.floor(Math.random() * 30000) + 10000,
    requests: Math.floor(Math.random() * 100) + 50,
  })),
  recentLogs: Array.from({ length: 20 }, (_, i) => ({
    id: `log-${i}`,
    timestamp: new Date(Date.now() - i * 60 * 60 * 1000).toISOString(),
    model: [
      "Claude 3 Sonnet (APAC)",
      "Claude 3.5 Sonnet (APAC)",
      "Claude 3 Haiku (APAC)",
    ][Math.floor(Math.random() * 3)],
    tokens: Math.floor(Math.random() * 5000) + 1000,
    duration: Math.floor(Math.random() * 3000) + 500,
    status: Math.random() > 0.1 ? "success" : "error",
  })),
};

// Axios 인스턴스
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
  timeout: 300000, // 5분
});

// 요청 인터셉터 - 인증 토큰 자동 추가
api.interceptors.request.use(async (config) => {
  console.log("API 요청:", config.method?.toUpperCase(), config.url);

  // 개발 모드에서 인증 스킵
  if (process.env.REACT_APP_SKIP_AUTH === "true") {
    console.log("🔓 개발 모드: 인증 스킵");
    return config;
  }

  // 인증이 필요한 요청에 토큰 추가
  try {
    // AuthContext에서 토큰 가져오기 (동적 import 사용)
    const { fetchAuthSession } = await import("aws-amplify/auth");
    const session = await fetchAuthSession();
    const token = session?.tokens?.idToken?.toString();

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log("✅ 인증 토큰 추가됨");
    } else {
      console.log("⚠️ 인증 토큰 없음");
    }
  } catch (error) {
    console.log("📝 인증 토큰 가져오기 실패:", error.message);
    // 인증 오류가 있어도 요청은 계속 진행 (public API도 있을 수 있음)
  }

  return config;
});

// 응답 인터셉터 - 401 오류 시 리다이렉션 처리
api.interceptors.response.use(
  (response) => {
    console.log("API 응답:", response.status, response.config.url);
    return response;
  },
  async (error) => {
    console.error("API 오류 상세:", {
      status: error.response?.status,
      message: error.message,
      code: error.code,
      url: error.config?.url,
      data: error.response?.data,
    });

    // 401 Unauthorized 오류 처리
    if (error.response?.status === 401) {
      console.log("🔐 인증 오류 발생 - 로그인 페이지로 리다이렉션");

      try {
        // 로그아웃 처리
        const { signOut } = await import("aws-amplify/auth");
        await signOut();

        // 로그인 페이지로 리다이렉션
        window.location.href = "/login";
      } catch (signOutError) {
        console.error("로그아웃 처리 실패:", signOutError);
        // 강제 리다이렉션
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);

// =============================================================================
// 🔄 데이터 매핑 유틸리티 함수들
// =============================================================================

/**
 * 프론트엔드 → 백엔드 데이터 변환
 */
const mapFrontendToBackend = {
  // 채팅 메시지 데이터 변환
  chatMessage: (frontendData) => ({
    userInput: frontendData.userInput || frontendData.message,
    chat_history: frontendData.chat_history || frontendData.messages || [],
    prompt_cards: frontendData.promptCards || frontendData.prompt_cards || [],
    modelId: frontendData.selectedModel || frontendData.modelId,
    conversationId: frontendData.conversationId || frontendData.conversation_id,
    userSub: frontendData.userId || frontendData.user_id,
    useKnowledgeBase: frontendData.useKnowledgeBase !== false, // 기본값: true (뉴스 요약 서비스에서는 항상 Knowledge Base 사용)
  }),

  // 프롬프트 카드 데이터 변환
  promptCard: (frontendData) => ({
    title: frontendData.title,
    prompt_text: frontendData.prompt_text || frontendData.content,
    tags: frontendData.tags || [],
    isActive: frontendData.enabled !== false && frontendData.isActive !== false,
    stepOrder: frontendData.stepOrder || 1,
  }),

  // 프로젝트 데이터 변환
  project: (frontendData) => ({
    name: frontendData.name,
    description: frontendData.description || "",
    tags: frontendData.tags || [],
    aiRole: frontendData.aiRole || "",
    aiInstructions: frontendData.aiInstructions || "",
    targetAudience: frontendData.targetAudience || "일반독자",
    outputFormat: frontendData.outputFormat || "multiple",
    styleGuidelines: frontendData.styleGuidelines || "",
  }),
};

/**
 * 백엔드 → 프론트엔드 데이터 변환
 */
const mapBackendToFrontend = {
  // 채팅 메시지 변환
  chatMessage: (backendData) => ({
    id: backendData.id || backendData.messageId || Date.now().toString(),
    role: backendData.role,
    content: backendData.content || backendData.text,
    timestamp:
      backendData.timestamp ||
      backendData.createdAt ||
      new Date().toISOString(),
    tokenCount: backendData.tokenCount || backendData.tokens_used,
  }),

  // 프롬프트 카드 변환
  promptCard: (backendData) => ({
    promptId: backendData.promptId || backendData.prompt_id,
    title: backendData.title,
    prompt_text: backendData.prompt_text || backendData.content,
    tags: backendData.tags || [],
    isActive: backendData.isActive !== false,
    enabled: backendData.isActive !== false,
    stepOrder: backendData.stepOrder || 1,
    createdAt: backendData.createdAt,
    updatedAt: backendData.updatedAt,
  }),

  // 프로젝트 변환
  project: (backendData) => ({
    projectId: backendData.projectId,
    name: backendData.name,
    description: backendData.description || "",
    status: backendData.status,
    tags: backendData.tags || [],
    aiRole: backendData.aiRole || "",
    aiInstructions: backendData.aiInstructions || "",
    targetAudience: backendData.targetAudience || "일반독자",
    outputFormat: backendData.outputFormat || "multiple",
    styleGuidelines: backendData.styleGuidelines || "",
    createdAt: backendData.createdAt,
    updatedAt: backendData.updatedAt,
    promptCount: backendData.promptCount || 0,
    conversationCount: backendData.conversationCount || 0,
  }),

  // 대화 목록 변환
  conversation: (backendData) => ({
    id: backendData.id || backendData.conversationId,
    title: backendData.title,
    startedAt: backendData.startedAt || backendData.createdAt,
    lastActivityAt: backendData.lastActivityAt || backendData.updatedAt,
    tokenSum: backendData.tokenSum || backendData.totalTokens || 0,
  }),
};

/**
 * Mock 데이터와 실제 API 간 전환을 위한 플래그
 */
const USE_MOCK_DATA = process.env.REACT_APP_USE_MOCK_DATA === "true";

/**
 * 🔍 API 연결 상태 확인 함수
 */
export const testApiConnection = async () => {
  console.log("🔍 API 연결 상태 확인 중...");
  console.log("- API Base URL:", API_BASE_URL);
  console.log("- Use Mock Data:", USE_MOCK_DATA);
  console.log("- Node Env:", process.env.NODE_ENV);

  try {
    // 간단한 헬스체크 엔드포인트 호출
    const response = await api.get("/health");
    console.log("✅ API 연결 성공:", response.status);
    return { success: true, status: response.status, data: response.data };
  } catch (error) {
    console.log("❌ API 연결 실패:", error.message);
    console.log("- Status:", error.response?.status);
    console.log("- Error Code:", error.code);
    return {
      success: false,
      error: error.message,
      status: error.response?.status,
      code: error.code,
    };
  }
};

// =============================================================================
// 프로젝트 API (기존 유지)
// =============================================================================

export const projectAPI = {
  getProjects: async () => {
    try {
      const response = await api.get("/projects");
      // 백엔드 데이터를 프론트엔드 형식으로 변환
      const projects = response.data.projects || response.data;
      return {
        projects: Array.isArray(projects)
          ? projects.map(mapBackendToFrontend.project)
          : [],
        count: response.data.count || projects.length,
        hasMore: response.data.hasMore || false,
        nextKey: response.data.nextKey,
      };
    } catch (error) {
      console.error("프로젝트 목록 조회 실패:", error);
      throw error;
    }
  },

  getProject: async (projectId) => {
    try {
      const response = await api.get(`/projects/${projectId}`);
      // 백엔드 데이터를 프론트엔드 형식으로 변환
      return mapBackendToFrontend.project(response.data);
    } catch (error) {
      console.error("프로젝트 상세 조회 실패:", error);
      throw error;
    }
  },

  createProject: async (projectData) => {
    try {
      // 프론트엔드 데이터를 백엔드 형식으로 변환
      const backendData = mapFrontendToBackend.project(projectData);
      const response = await api.post("/projects", backendData);
      // 응답을 프론트엔드 형식으로 변환
      return mapBackendToFrontend.project(response.data);
    } catch (error) {
      console.error("프로젝트 생성 실패:", error);
      throw error;
    }
  },

  updateProject: async (projectId, projectData) => {
    try {
      // 프론트엔드 데이터를 백엔드 형식으로 변환
      const backendData = mapFrontendToBackend.project(projectData);
      const response = await api.put(`/projects/${projectId}`, backendData);
      // 응답을 프론트엔드 형식으로 변환
      return mapBackendToFrontend.project(response.data);
    } catch (error) {
      console.error("프로젝트 업데이트 실패:", error);
      throw error;
    }
  },

  deleteProject: async (projectId) => {
    try {
      const response = await api.delete(`/projects/${projectId}`);
      return response.data;
    } catch (error) {
      console.error("프로젝트 삭제 실패:", error);
      throw error;
    }
  },

  getUploadUrl: async (projectId, fileName) => {
    try {
      const response = await api.get(`/projects/${projectId}/upload-url`, {
        params: { fileName },
      });
      return response.data;
    } catch (error) {
      console.error("업로드 URL 생성 실패:", error);
      throw error;
    }
  },
};

// =============================================================================
// 프롬프트 카드 API (기존 유지)
// =============================================================================

export const promptCardAPI = {
  getPromptCards: async (
    projectId,
    includeContent = false,
    includeStats = false
  ) => {
    try {
      const response = await api.get(`/prompts/${projectId}`, {
        params: { includeContent, includeStats },
      });

      // 백엔드 응답을 프론트엔드 형식으로 변환
      const promptCards =
        response.data.promptCards || response.data.prompts || response.data;
      return {
        promptCards: Array.isArray(promptCards)
          ? promptCards.map(mapBackendToFrontend.promptCard)
          : [],
        count: response.data.count || promptCards.length,
      };
    } catch (error) {
      console.error("프롬프트 카드 목록 조회 실패:", error);
      throw error;
    }
  },

  createPromptCard: async (projectId, promptData) => {
    try {
      // 프론트엔드 데이터를 백엔드 형식으로 변환
      const backendData = mapFrontendToBackend.promptCard(promptData);
      const response = await api.post(`/prompts/${projectId}`, backendData);
      // 응답을 프론트엔드 형식으로 변환
      return mapBackendToFrontend.promptCard(response.data);
    } catch (error) {
      console.error("프롬프트 카드 생성 실패:", error);
      throw error;
    }
  },

  updatePromptCard: async (projectId, promptId, promptData) => {
    try {
      // 프론트엔드 데이터를 백엔드 형식으로 변환
      const backendData = mapFrontendToBackend.promptCard(promptData);
      const response = await api.put(
        `/prompts/${projectId}/${promptId}`,
        backendData
      );
      // 응답을 프론트엔드 형식으로 변환
      return mapBackendToFrontend.promptCard(response.data);
    } catch (error) {
      console.error("프롬프트 카드 업데이트 실패:", error);
      throw error;
    }
  },

  getPromptContent: async (projectId, promptId) => {
    try {
      const response = await api.get(
        `/prompts/${projectId}/${promptId}/content`
      );
      return response.data;
    } catch (error) {
      console.error("프롬프트 내용 조회 실패:", error);
      throw error;
    }
  },

  deletePromptCard: async (projectId, promptId) => {
    try {
      const response = await api.delete(`/prompts/${projectId}/${promptId}`);
      return response.data;
    } catch (error) {
      console.error("프롬프트 카드 삭제 실패:", error);
      throw error;
    }
  },

  reorderPromptCards: async (projectId, reorderData) => {
    try {
      const updatePromises = reorderData.map(({ promptId, stepOrder }) =>
        api.put(`/prompts/${projectId}/${promptId}`, { stepOrder })
      );

      const responses = await Promise.all(updatePromises);
      return {
        message: "프롬프트 카드 순서가 업데이트되었습니다.",
        updatedCards: responses.map((r) =>
          mapBackendToFrontend.promptCard(r.data)
        ),
      };
    } catch (error) {
      console.error("프롬프트 카드 순서 변경 실패:", error);
      throw error;
    }
  },
};

// =============================================================================
// 🔧 완전 수정된 제목 생성 API
// =============================================================================

export const generateAPI = {
  generateTitle: async (projectId, data) => {
    console.log("대화 생성 요청 시작:", {
      projectId,
      inputLength: data.userInput?.length || 0,
      historyLength: data.chat_history?.length || 0,
      timestamp: new Date().toISOString(),
    });

    try {
      // 프론트엔드 데이터를 백엔드 형식으로 변환
      const backendData = mapFrontendToBackend.chatMessage(data);

      console.log("🔄 변환된 백엔드 데이터:", backendData);

      const response = await api.post(
        `/projects/${projectId}/generate`,
        backendData
      );

      console.log("대화 생성 성공:", {
        status: response.status,
        mode: response.data.mode,
        message: response.data.message,
        timestamp: new Date().toISOString(),
      });

      return response.data;
    } catch (error) {
      console.error("대화 생성 실패:", {
        code: error.code,
        message: error.message,
        status: error.response?.status,
        responseData: error.response?.data,
        timestamp: new Date().toISOString(),
      });
      throw error;
    }
  },

  // 🔧 실제 스트리밍 구현 - Server-Sent Events 사용
  generateTitleStream: async (
    projectId,
    data,
    onChunk,
    onError,
    onComplete
  ) => {
    console.log("스트리밍 대화 생성 요청 시작:", {
      projectId,
      inputLength: data.userInput?.length || 0,
      historyLength: data.chat_history?.length || 0,
      timestamp: new Date().toISOString(),
    });

    // 프론트엔드 데이터를 백엔드 형식으로 변환 (try-catch 밖에서 정의)
    const backendData = mapFrontendToBackend.chatMessage(data);
    console.log("🔄 스트리밍용 변환된 데이터:", backendData);

    try {
      // 1. 먼저 실제 스트리밍 API 시도
      const streamingUrl = `${API_BASE_URL}/projects/${projectId}/generate/stream`;

      console.log("🚀 실제 스트리밍 API 시도:", streamingUrl);

      // 인증 토큰 가져오기
      let authHeaders = {};
      try {
        const { fetchAuthSession } = await import("aws-amplify/auth");
        const session = await fetchAuthSession();
        const token = session?.tokens?.idToken?.toString();
        if (token) {
          authHeaders.Authorization = `Bearer ${token}`;
        }
      } catch (authError) {
        console.log("인증 토큰 가져오기 실패:", authError.message);
      }

      const response = await fetch(streamingUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          ...authHeaders, // 인증 토큰 포함
        },
        body: JSON.stringify(backendData), // 변환된 데이터 사용
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // 2. 응답이 스트리밍 형식인지 확인
      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("text/event-stream")) {
        console.log("❌ 스트리밍 응답이 아님, 폴백 처리");
        throw new Error("스트리밍 응답이 아닙니다");
      }

      // 3. 실제 스트리밍 처리
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let fullResponse = "";

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const eventData = JSON.parse(line.slice(6));

                if (eventData.type === "start") {
                  console.log("✅ 스트리밍 시작");
                } else if (eventData.type === "chunk") {
                  fullResponse += eventData.response;
                  if (onChunk) {
                    onChunk(eventData.response, {
                      content: eventData.response,
                    });
                  }
                } else if (eventData.type === "complete") {
                  console.log("✅ 스트리밍 완료");
                  if (onComplete) {
                    onComplete({
                      result: eventData.fullResponse || fullResponse,
                      timestamp: new Date().toISOString(),
                    });
                  }
                  return { result: eventData.fullResponse || fullResponse };
                } else if (eventData.type === "error") {
                  throw new Error(eventData.error);
                }
              } catch (parseError) {
                console.error("JSON 파싱 오류:", parseError);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }

      return { result: fullResponse };
    } catch (streamError) {
      console.log("⚠️ 스트리밍 실패, 폴백 처리:", streamError.message);

      // 4. 폴백: 일반 API 호출
      try {
        const fallbackResponse = await api.post(
          `/projects/${projectId}/generate`,
          backendData // 변환된 데이터 사용
        );

        console.log("✅ 폴백 API 성공:", {
          mode: fallbackResponse.data.mode,
          timestamp: new Date().toISOString(),
        });

        // 폴백 응답을 스트리밍처럼 시뮬레이션
        if (fallbackResponse.data.result && onChunk) {
          const fullText = fallbackResponse.data.result;
          const words = fullText.split(" ");

          for (let i = 0; i < words.length; i++) {
            const word = words[i] + (i < words.length - 1 ? " " : "");
            onChunk(word, { content: word });
            await new Promise((resolve) => setTimeout(resolve, 30));
          }
        }

        // 완료 콜백 호출
        if (onComplete) {
          onComplete({
            result: fallbackResponse.data.result,
            model_info: fallbackResponse.data.model_info,
            performance_metrics: fallbackResponse.data.performance_metrics,
            timestamp: new Date().toISOString(),
          });
        }

        return fallbackResponse.data;
      } catch (fallbackError) {
        console.error("❌ 폴백 API도 실패:", fallbackError);
        if (onError) {
          onError(
            new Error("서비스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.")
          );
        }
        throw new Error("서비스를 사용할 수 없습니다.");
      }
    }
  },

  getExecutionStatus: async (executionArn) => {
    return {
      status: "SUCCEEDED",
      output: "{}",
    };
  },
};

// =============================================================================
// 채팅 API (기존 유지)
// =============================================================================

export const chatAPI = {
  sendMessage: async (projectId, message, sessionId, userId = "default") => {
    console.log("채팅 메시지를 generate API로 전달:", {
      projectId,
      message,
      sessionId,
      userId,
    });

    try {
      const response = await generateAPI.generateTitle(projectId, {
        userInput: message,
        userRequest: "",
        chat_history: [],
      });

      return {
        response: response.result,
        sessionId,
        userId,
        timestamp: new Date().toISOString(),
        mode: response.mode || "chat",
      };
    } catch (error) {
      console.error("채팅 메시지 처리 실패:", error);
      throw error;
    }
  },

  getChatHistory: async (projectId, sessionId, userId = "default") => {
    console.log("채팅 히스토리 조회:", { projectId, sessionId, userId });

    return {
      messages: [],
      sessionId,
      userId,
      message:
        "채팅 히스토리는 현재 지원되지 않습니다. 각 메시지는 독립적으로 처리됩니다.",
    };
  },

  getChatSessions: async (projectId, userId = "default") => {
    console.log("채팅 세션 목록 조회:", { projectId, userId });

    return {
      sessions: [],
      message:
        "채팅 세션은 현재 지원되지 않습니다. 각 대화는 독립적으로 처리됩니다.",
    };
  },

  deleteChatSession: async (projectId, sessionId, userId = "default") => {
    console.log("채팅 세션 삭제:", { projectId, sessionId, userId });

    return {
      message: "채팅 세션 삭제가 완료되었습니다.",
      sessionId,
      userId,
    };
  },
};

// =============================================================================
// 인증 API (기존 유지)
// =============================================================================

export const authAPI = {
  isAuthenticated: () => {
    return true;
  },

  getCurrentUser: () => {
    return {
      id: "user",
      email: "user@example.com",
      name: "사용자",
    };
  },

  signin: async (credentials) => {
    const response = await api.post("/auth/signin", credentials);
    return response.data;
  },

  signup: async (userData) => {
    const response = await api.post("/auth/signup", userData);
    return response.data;
  },

  signout: async () => {
    const response = await api.post("/auth/signout");
    return response.data;
  },

  verifyEmail: async (verificationData) => {
    const response = await api.post("/auth/verify-email", verificationData);
    return response.data;
  },

  forgotPassword: async (email) => {
    const response = await api.post("/auth/forgot-password", { email });
    return response.data;
  },

  confirmPassword: async (resetData) => {
    const response = await api.post("/auth/confirm-password", resetData);
    return response.data;
  },

  // 비밀번호 찾기 - 인증번호 발송
  requestPasswordReset: async (email) => {
    const response = await api.post("/auth/forgot-password", { email });
    return response.data;
  },

  // 비밀번호 재설정 - 인증번호와 새 비밀번호로 재설정
  resetPassword: async (resetData) => {
    const response = await api.post("/auth/confirm-password", {
      email: resetData.email,
      code: resetData.code,
      newPassword: resetData.newPassword,
    });
    return response.data;
  },
};

// =============================================================================
// 🔧 개선된 오류 처리 함수
// =============================================================================

export const handleAPIError = async (error) => {
  console.error("API 오류 상세 분석:", {
    message: error.message,
    code: error.code,
    status: error.response?.status,
    statusText: error.response?.statusText,
    data: error.response?.data,
    timestamp: new Date().toISOString(),
  });

  // 401 Unauthorized 특별 처리 - 로그인 페이지로 리다이렉트
  if (error.response?.status === 401) {
    try {
      // AuthContext에서 로그아웃 처리
      const { signOut } = await import("aws-amplify/auth");
      await signOut();

      // 로그인 페이지로 리다이렉트
      window.location.href = "/auth/signin";

      return {
        userMessage: "인증이 만료되었습니다. 다시 로그인해주세요.",
        statusCode: 401,
        errorType: "UNAUTHORIZED",
        shouldRedirect: true,
      };
    } catch (signOutError) {
      console.error("로그아웃 처리 실패:", signOutError);
      // 로그아웃 실패해도 리다이렉트
      window.location.href = "/auth/signin";
      return {
        userMessage: "인증이 만료되었습니다. 다시 로그인해주세요.",
        statusCode: 401,
        errorType: "UNAUTHORIZED",
        shouldRedirect: true,
      };
    }
  }

  // 403 Forbidden 특별 처리
  if (error.response?.status === 403) {
    return {
      userMessage: "API 접근이 차단되었습니다. 관리자에게 문의하세요.",
      statusCode: 403,
      errorType: "FORBIDDEN",
      shouldRedirect: false,
    };
  }

  // Gateway Timeout 특별 처리
  if (error.response?.status === 504) {
    return {
      userMessage:
        "서버 응답 시간이 초과되었습니다. 요청을 간소화하거나 잠시 후 다시 시도해주세요.",
      statusCode: 504,
      errorType: "GATEWAY_TIMEOUT",
      shouldRedirect: false,
    };
  }

  // CORS 오류 특별 처리
  if (
    error.message?.includes("CORS") ||
    error.code === "ERR_NETWORK" ||
    error.message?.includes("Access-Control-Allow-Origin")
  ) {
    return {
      userMessage:
        "서버 연결 설정에 문제가 있습니다. 페이지를 새로고침하고 다시 시도해주세요.",
      statusCode: 0,
      errorType: "CORS_ERROR",
      shouldRedirect: false,
    };
  }

  // 타임아웃 오류 특별 처리
  if (error.code === "ECONNABORTED") {
    return {
      userMessage:
        "요청 처리 시간이 초과되었습니다. 입력을 줄이거나 잠시 후 다시 시도해주세요.",
      statusCode: 0,
      errorType: "TIMEOUT_ERROR",
      shouldRedirect: false,
    };
  }

  if (error.response) {
    const status = error.response.status;
    const message =
      error.response.data?.message ||
      error.response.data?.error ||
      "서버 오류가 발생했습니다";

    switch (status) {
      case 400:
        return {
          userMessage: `잘못된 요청: ${message}`,
          statusCode: 400,
          shouldRedirect: false,
        };
      case 404:
        return {
          userMessage: "요청한 리소스를 찾을 수 없습니다",
          statusCode: 404,
          shouldRedirect: false,
        };
      case 429:
        return {
          userMessage: "요청이 너무 많습니다. 잠시 후 다시 시도해주세요",
          statusCode: 429,
          shouldRedirect: false,
        };
      case 500:
        return {
          userMessage: "서버 내부 오류가 발생했습니다",
          statusCode: 500,
          shouldRedirect: false,
        };
      default:
        return {
          userMessage: `서버 오류 (${status}): ${message}`,
          statusCode: status,
          shouldRedirect: false,
        };
    }
  } else if (error.request) {
    return {
      userMessage: "서버에 연결할 수 없습니다. 네트워크 연결을 확인해주세요",
      statusCode: 0,
      errorType: "NETWORK_ERROR",
      shouldRedirect: false,
    };
  } else {
    return {
      userMessage: `요청 오류: ${error.message}`,
      statusCode: -1,
      errorType: "REQUEST_ERROR",
      shouldRedirect: false,
    };
  }
};

// =============================================================================
// 기타 유틸리티 함수들 (기존 유지)
// =============================================================================

export const DYNAMIC_PROMPT_SYSTEM = {
  message:
    "원하는 만큼 프롬프트 카드를 생성하여 나만의 AI 어시스턴트를 만들어보세요!",
  maxPromptCards: 50,
  supportedFormats: ["text", "markdown"],
  defaultStepOrder: 1,
};

export const COLOR_OPTIONS = [
  {
    id: "blue",
    name: "파랑",
    bgClass: "bg-blue-100",
    textClass: "text-blue-800",
    borderClass: "border-blue-200",
  },
  {
    id: "green",
    name: "초록",
    bgClass: "bg-green-100",
    textClass: "text-green-800",
    borderClass: "border-green-200",
  },
  {
    id: "purple",
    name: "보라",
    bgClass: "bg-purple-100",
    textClass: "text-purple-800",
    borderClass: "border-purple-200",
  },
  {
    id: "orange",
    name: "주황",
    bgClass: "bg-orange-100",
    textClass: "text-orange-800",
    borderClass: "border-orange-200",
  },
  {
    id: "red",
    name: "빨강",
    bgClass: "bg-red-100",
    textClass: "text-red-800",
    borderClass: "border-red-200",
  },
  {
    id: "indigo",
    name: "남색",
    bgClass: "bg-indigo-100",
    textClass: "text-indigo-800",
    borderClass: "border-indigo-200",
  },
  {
    id: "pink",
    name: "분홍",
    bgClass: "bg-pink-100",
    textClass: "text-pink-800",
    borderClass: "border-pink-200",
  },
  {
    id: "yellow",
    name: "노랑",
    bgClass: "bg-yellow-100",
    textClass: "text-yellow-800",
    borderClass: "border-yellow-200",
  },
  {
    id: "gray",
    name: "회색",
    bgClass: "bg-gray-100",
    textClass: "text-gray-800",
    borderClass: "border-gray-200",
  },
];

export const getPromptCardInfo = (promptCard) => {
  return {
    id: promptCard.promptId || promptCard.id,
    title: promptCard.title || "새 프롬프트 카드",
    color: promptCard.color || "gray",
    description: promptCard.description || "",
    stepOrder: promptCard.stepOrder || 1,
    isActive: promptCard.isActive !== false,
  };
};

export const filterProjects = (projects, filters) => {
  let filtered = [...projects];

  if (filters.searchQuery) {
    const query = filters.searchQuery.toLowerCase();
    filtered = filtered.filter(
      (project) =>
        project.name?.toLowerCase().includes(query) ||
        project.description?.toLowerCase().includes(query) ||
        project.tags?.some((tag) => tag.toLowerCase().includes(query))
    );
  }

  switch (filters.sortBy) {
    case "created":
      filtered.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
      break;
    case "updated":
      filtered.sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt));
      break;
    case "name":
      filtered.sort((a, b) => a.name?.localeCompare(b.name));
      break;
    default:
      break;
  }

  return filtered;
};

export const formatTokenCount = (count) => {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}K`;
  }
  return count.toString();
};

export const formatFileSize = (bytes) => {
  if (bytes >= 1024) {
    return `${(bytes / 1024).toFixed(1)}KB`;
  }
  return `${bytes}B`;
};

export const calculatePromptStats = (promptCards) => {
  if (!promptCards || promptCards.length === 0) {
    return {
      totalCards: 0,
      totalTokens: 0,
      averageTokens: 0,
      activeCards: 0,
      maxStepOrder: 0,
      hasCustomOrder: false,
    };
  }

  const activeCards = promptCards.filter((card) => card.isActive !== false);
  const totalTokens = activeCards.reduce((sum, card) => {
    return sum + (card.tokenCount || card.contentLength || 0);
  }, 0);

  const stepOrders = activeCards
    .map((card) => card.stepOrder || 0)
    .filter((step) => step > 0);
  const hasCustomOrder = stepOrders.length > 0;
  const maxStepOrder = stepOrders.length > 0 ? Math.max(...stepOrders) : 0;

  return {
    totalCards: promptCards.length,
    activeCards: activeCards.length,
    totalTokens,
    averageTokens:
      activeCards.length > 0 ? Math.round(totalTokens / activeCards.length) : 0,
    maxStepOrder,
    hasCustomOrder,
    stepOrderRange: {
      min: stepOrders.length > 0 ? Math.min(...stepOrders) : 0,
      max: maxStepOrder,
    },
  };
};

// =============================================================================
// Usage API (Dashboard용)
// =============================================================================

export const getUsage = async (range = "month") => {
  console.log("사용량 데이터 조회 요청:", { range });

  // Mock 데이터 사용 모드이거나 개발 모드일 때
  if (USE_MOCK_DATA || process.env.NODE_ENV === "development") {
    console.log("🔄 Mock 사용량 데이터 반환");
    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 500));
    return mockUsageData;
  }

  try {
    const response = await api.get(`/usage?range=${range}`);
    console.log("✅ 사용량 API 호출 성공");
    return response.data;
  } catch (error) {
    console.warn("⚠️ 사용량 API 호출 실패, Mock 데이터로 폴백:", error.message);
    // Fallback to mock data
    return mockUsageData;
  }
};

// =============================================================================
// 🆕 Conversation History API
// =============================================================================

export const conversationAPI = {
  // 대화 목록 조회 (무한 스크롤)
  getConversations: async (cursor, limit = 20) => {
    console.log("대화 목록 조회 시작:", { cursor, limit, API_BASE_URL });

    const params = new URLSearchParams({ limit: limit.toString() });
    if (cursor) {
      params.append("cursor", cursor);
    }

    const url = `/conversations?${params}`;
    console.log("API 요청 URL:", `${API_BASE_URL}${url}`);

    try {
      const response = await api.get(url);
      console.log("대화 목록 조회 성공:", response.data);

      // 백엔드 응답을 프론트엔드 형식으로 변환
      const conversations =
        response.data.conversations || response.data.items || response.data;
      return {
        conversations: Array.isArray(conversations)
          ? conversations.map(mapBackendToFrontend.conversation)
          : [],
        hasMore: response.data.hasMore || false,
        nextCursor: response.data.nextCursor || response.data.cursor,
      };
    } catch (error) {
      console.error("대화 목록 조회 실패:", error);
      // Mock 데이터로 폴백 (개발 시)
      if (USE_MOCK_DATA || process.env.NODE_ENV === "development") {
        console.log("🔄 Mock 데이터로 폴백");
        return {
          conversations: mockConversations,
          hasMore: false,
          nextCursor: null,
        };
      }
      throw error;
    }
  },

  // 새 대화 생성
  createConversation: async (title = "New Conversation") => {
    console.log("새 대화 생성:", { title });

    try {
      const response = await api.post("/conversations", { title });
      return response.data;
    } catch (error) {
      console.error("대화 생성 실패:", error);
      throw error;
    }
  },

  // 특정 대화의 메시지 조회 (페이징)
  getMessages: async (conversationId, cursor, limit = 50) => {
    console.log("메시지 조회:", { conversationId, cursor, limit });

    const params = new URLSearchParams({
      convId: conversationId,
      limit: limit.toString(),
    });
    if (cursor) {
      params.append("cursor", cursor);
    }

    try {
      const response = await api.get(`/messages?${params}`);

      // 백엔드 응답을 프론트엔드 형식으로 변환
      const messages =
        response.data.messages || response.data.items || response.data;
      return {
        messages: Array.isArray(messages)
          ? messages.map(mapBackendToFrontend.chatMessage)
          : [],
        hasMore: response.data.hasMore || false,
        nextCursor: response.data.nextCursor || response.data.cursor,
      };
    } catch (error) {
      console.error("메시지 조회 실패:", error);
      // Mock 데이터로 폴백 (개발 시)
      if (USE_MOCK_DATA || process.env.NODE_ENV === "development") {
        console.log("🔄 Mock 메시지 데이터로 폴백");
        const mockMessageData = mockMessages[conversationId] || [];
        return {
          messages: mockMessageData,
          hasMore: false,
          nextCursor: null,
        };
      }
      throw error;
    }
  },

  // 대화 삭제
  deleteConversation: async (conversationId) => {
    console.log("대화 삭제:", { conversationId });

    try {
      const response = await api.delete(`/conversations/${conversationId}`);
      console.log("대화 삭제 성공:", response.data);
      return response.data;
    } catch (error) {
      console.error("대화 삭제 실패:", error);
      throw error;
    }
  },

  // 대화 업데이트 (제목 등)
  updateConversation: async (conversationId, updates) => {
    console.log("대화 업데이트:", { conversationId, updates });

    try {
      const response = await api.put(
        `/conversations/${conversationId}`,
        updates
      );
      console.log("대화 업데이트 성공:", response.data);
      return response.data;
    } catch (error) {
      console.error("대화 업데이트 실패:", error);
      throw error;
    }
  },
};

// Mock data for conversation development
export const mockConversations = [
  {
    id: "1",
    title: "서울경제신문 AI 제목 생성 테스트",
    startedAt: "2025-01-20T10:30:00Z",
    lastActivityAt: "2025-01-20T15:45:00Z",
    tokenSum: 1250,
  },
  {
    id: "2",
    title: "경제 뉴스 헤드라인 최적화",
    startedAt: "2025-01-19T14:20:00Z",
    lastActivityAt: "2025-01-19T16:30:00Z",
    tokenSum: 890,
  },
  {
    id: "3",
    title: "부동산 시장 분석 제목 생성",
    startedAt: "2025-01-18T09:15:00Z",
    lastActivityAt: "2025-01-18T11:45:00Z",
    tokenSum: 2150,
  },
];

export const mockMessages = {
  1: [
    {
      id: "2025-01-20T10:30:00.000Z",
      role: "user",
      content: "오늘 서울 부동산 시장 현황에 대한 기사 제목을 만들어주세요.",
      tokenCount: 25,
      timestamp: "2025-01-20T10:30:00.000Z",
    },
    {
      id: "2025-01-20T10:30:05.000Z",
      role: "assistant",
      content:
        '서울 부동산 시장 현황에 대한 몇 가지 제목 옵션을 제안해드리겠습니다:\n\n1. "서울 아파트값 3개월 연속 하락세... 매수심리 위축"\n2. "강남·서초구 고가 아파트 거래 급감, 시장 관망세 지속"\n3. "서울 부동산 시장 \'관망론\' 확산... 전세시장은 여전히 불안"',
      tokenCount: 95,
      timestamp: "2025-01-20T10:30:05.000Z",
    },
  ],
  2: [
    {
      id: "2025-01-19T14:20:00.000Z",
      role: "user",
      content: "반도체 산업 관련 경제 뉴스 제목을 생성해주세요.",
      tokenCount: 20,
      timestamp: "2025-01-19T14:20:00.000Z",
    },
    {
      id: "2025-01-19T14:20:03.000Z",
      role: "assistant",
      content:
        '반도체 산업 관련 경제 뉴스 제목들을 제안드립니다:\n\n1. "삼성전자 메모리 반도체 수요 회복 기대감... 주가 상승세"\n2. "AI 칩 수요 급증에 SK하이닉스 4분기 실적 개선 전망"\n3. "중국 반도체 굴기 vs 한국 기술력... 글로벌 경쟁 심화"',
      tokenCount: 78,
      timestamp: "2025-01-19T14:20:03.000Z",
    },
  ],
};

// =============================================================================
// 🧪 연결 테스트 및 상태 확인 함수들
// =============================================================================

/**
 * 🧪 REST API 연결 테스트 함수
 */
export const testAPIConnection = async () => {
  try {
    console.log("🔍 API 연결 테스트 시작...");

    const response = await api.get("/health", {
      timeout: 5000, // 5초 타임아웃
    });

    console.log("✅ API 연결 테스트 성공:", response.data);
    return {
      success: true,
      message: "백엔드 서버 연결 성공",
      data: response.data,
    };
  } catch (error) {
    console.error("❌ API 연결 테스트 실패:", error);

    let errorMessage = "백엔드 서버 연결 실패";
    if (error.code === "ECONNABORTED") {
      errorMessage = "연결 시간 초과 - 서버가 응답하지 않습니다";
    } else if (error.response?.status === 404) {
      errorMessage = "health 엔드포인트가 존재하지 않습니다";
    } else if (error.response?.status >= 500) {
      errorMessage = "서버 내부 오류가 발생했습니다";
    } else if (!error.response) {
      errorMessage = "네트워크 연결 오류 - 서버에 도달할 수 없습니다";
    }

    return {
      success: false,
      message: errorMessage,
      error: error.message,
      status: error.response?.status,
    };
  }
};

/**
 * 🔄 종합 연결 상태 확인 (REST API + WebSocket)
 */
export const checkConnectionStatus = async () => {
  console.log("🔍 종합 연결 상태 확인 시작...");

  const results = {
    timestamp: new Date().toISOString(),
    restApi: null,
    websocket: null,
    authentication: null,
  };

  // 1. REST API 연결 테스트
  try {
    results.restApi = await testAPIConnection();
  } catch (error) {
    results.restApi = {
      success: false,
      message: "REST API 테스트 중 오류 발생",
      error: error.message,
    };
  }

  // 2. 인증 상태 확인
  try {
    const { fetchAuthSession } = await import("aws-amplify/auth");
    const session = await fetchAuthSession();
    const token = session?.tokens?.idToken?.toString();

    results.authentication = {
      success: !!token,
      message: token ? "인증 토큰 확인됨" : "인증 토큰 없음",
      hasToken: !!token,
    };
  } catch (error) {
    results.authentication = {
      success: false,
      message: "인증 상태 확인 실패",
      error: error.message,
    };
  }

  // 3. WebSocket URL 확인
  try {
    const wsUrl = process.env.REACT_APP_WS_URL;
    results.websocket = {
      success:
        !!wsUrl && (wsUrl.startsWith("wss://") || wsUrl.startsWith("ws://")),
      message: !!wsUrl ? "WebSocket URL 설정됨" : "WebSocket URL 미설정",
      url: wsUrl ? wsUrl.replace(/token=[^&]+/, "token=***") : null,
    };
  } catch (error) {
    results.websocket = {
      success: false,
      message: "WebSocket 설정 확인 실패",
      error: error.message,
    };
  }

  console.log("📊 종합 연결 상태 결과:", results);
  return results;
};

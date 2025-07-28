import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { toast } from "react-hot-toast";
import { useWebSocket } from "./useWebSocket";
import { useThinkingProcess } from "./useThinkingProcess";
import { handleAPIError } from "../services/api";
import { useAuth } from "../contexts/AuthContext";

/**
 * 채팅 기능을 위한 커스텀 훅
 * @param {Array} promptCards - 프롬프트 카드 배열
 * @param {string} conversationId - 대화 ID (선택적)
 * @param {Function} createConversationFn - 대화 생성 함수
 * @param {Function} setCurrentConversationFn - 현재 대화 설정 함수
 * @param {Function} addConversationFn - 대화 추가 함수
 * @returns {Object} - 채팅 관련 상태와 함수들
 */
export const useChat = (
  promptCards = [],
  conversationId = null,
  createConversationFn = null,
  setCurrentConversationFn = null,
  addConversationFn = null,
  thinkingProcessActions = null
) => {
  const { user } = useAuth(); // Add user from AuthContext

  // 🎯 사고과정 관리 (thinkingProcessActions가 제공된 경우에만)
  const { addStep, completeStep, startThinking, finishThinking } =
    thinkingProcessActions || {};

  // 디버깅 로그 (첫 번째 렌더링에만)
  const isFirstRender = useRef(true);
  if (isFirstRender.current) {
    console.log("🔍 useChat 초기화");
    isFirstRender.current = false;
  }

  // conversationId 변경 감지
  useEffect(() => {
    console.log("🔄 conversationId 변경:", conversationId);
  }, [conversationId]);
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [copiedMessage, setCopiedMessage] = useState(null);
  const [canSendMessage, setCanSendMessage] = useState(true);
  const [inputHeight, setInputHeight] = useState(24); // 동적 높이 관리
  const [selectedModel, setSelectedModel] = useState(
    "apac.anthropic.claude-3-haiku-20240307-v1:0"
  );
  const streamingMessageIdRef = useRef(null);
  const currentWebSocketRef = useRef(null);
  const currentExecutionIdRef = useRef(null);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // 사용자 스크롤 상태 추적
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const scrollContainerRef = useRef(null);
  const lastScrollTopRef = useRef(0);

  // WebSocket 훅 추가
  const {
    isConnected: wsConnected,
    isConnecting: wsConnecting,
    error: wsError,
    startStreaming: wsStartStreaming,
    addMessageListener,
    removeMessageListener,
  } = useWebSocket();

  // 초기 메시지 설정 - conversationId 변경시 초기화
  useEffect(() => {
    console.log("💬 메시지 초기화");
    setMessages([]); // 빈 배열로 시작
  }, [conversationId]);

  // 사용자 스크롤 감지 함수
  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current) return;

    const container = scrollContainerRef.current;
    const currentScrollTop = container.scrollTop;
    const maxScrollTop = container.scrollHeight - container.clientHeight;

    // 사용자가 수동으로 스크롤했는지 감지
    if (Math.abs(currentScrollTop - lastScrollTopRef.current) > 2) {
      const isAtBottom = currentScrollTop >= maxScrollTop - 20;

      // 하단에 있을 때만 자동 스크롤 허용, 그 외는 사용자 스크롤 모드
      setIsUserScrolling(!isAtBottom);
    }

    lastScrollTopRef.current = currentScrollTop;
  }, []);

  const scrollToBottom = useCallback(() => {
    // 사용자가 스크롤 중이 아닐 때만 자동 스크롤
    if (!isUserScrolling && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [isUserScrolling]);

  // 메시지 추가 시 스크롤 하단으로 (사용자 스크롤 중이 아닐 때만)
  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // WebSocket 메시지 리스너 설정
  useEffect(() => {
    const handleWebSocketMessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log("WebSocket 메시지 수신:", data);

        const currentStreamingId = streamingMessageIdRef.current;

        switch (data.type) {
          case "stream_start":
            console.log("WebSocket 스트리밍 시작");
            break;

          case "progress":
            // 진행 상황 로그만 남기고 UI 업데이트는 제거
            console.log(`진행 상황: ${data.step} (${data.progress}%)`);
            break;

          case "stream_chunk":
            if (currentStreamingId) {
              setMessages((prev) => {
                const updatedMessages = [...prev];
                const streamingMsgIndex = updatedMessages.findIndex(
                  (msg) => msg.id === currentStreamingId
                );

                console.log("🎬 실시간 타이핑 청크 처리:", {
                  currentStreamingId,
                  streamingMsgIndex,
                  chunkIndex: data.chunk_index,
                  totalChunks: data.total_chunks,
                  content: data.content,
                });

                if (streamingMsgIndex !== -1) {
                  // 기존 내용에 새 청크 추가 (실시간 타이핑 효과)
                  const currentContent =
                    updatedMessages[streamingMsgIndex].content || "";

                  updatedMessages[streamingMsgIndex] = {
                    ...updatedMessages[streamingMsgIndex],
                    content: currentContent + data.content,
                    isLoading: true,
                    isStreaming: true,
                    // 🎯 타이핑 진행 상황 표시
                    typingProgress: {
                      currentChunk: data.chunk_index || 0,
                      totalChunks: data.total_chunks || 1,
                      isTyping: true,
                    },
                  };

                  console.log("✨ 실시간 타이핑 메시지 업데이트:", {
                    contentLength:
                      updatedMessages[streamingMsgIndex].content.length,
                    progress: `${data.chunk_index || 0}/${
                      data.total_chunks || 1
                    }`,
                  });
                } else {
                  console.log(
                    "스트리밍 메시지를 찾을 수 없음, 메시지 ID들:",
                    prev.map((m) => m.id)
                  );
                }

                return updatedMessages;
              });
              // 스트리밍 중에는 사용자가 스크롤 중이 아닐 때만 자동 스크롤
              if (!isUserScrolling) {
                scrollToBottom();
              }
            } else {
              console.log("currentStreamingId가 null임");
            }
            break;

          case "stream_complete":
            if (currentStreamingId) {
              setMessages((prev) => {
                const updatedMessages = [...prev];
                const streamingMsgIndex = updatedMessages.findIndex(
                  (msg) => msg.id === currentStreamingId
                );

                if (streamingMsgIndex !== -1) {
                  updatedMessages[streamingMsgIndex] = {
                    ...updatedMessages[streamingMsgIndex],
                    content: data.fullContent,
                    sources: data.sources || [], // Knowledge Base 출처 정보 추가
                    thinkingProcess: data.thinkingProcess || [], // Enhanced Agent System 사고 과정 추가
                    isLoading: false,
                    isStreaming: false,
                    timestamp: new Date().toISOString(),
                  };
                }

                return updatedMessages;
              });
              streamingMessageIdRef.current = null;
              scrollToBottom();
            }
            break;

          case "error":
            console.error("WebSocket 스트리밍 오류:", data.message);
            if (currentStreamingId) {
              setMessages((prev) => {
                const updatedMessages = [...prev];
                const streamingMsgIndex = updatedMessages.findIndex(
                  (msg) => msg.id === currentStreamingId
                );

                if (streamingMsgIndex !== -1) {
                  // 오류 유형에 따른 사용자 메시지 결정
                  let errorContent =
                    "메시지 처리 중 오류가 발생했습니다. 다시 시도해주세요.";

                  if (
                    data.message?.includes("401") ||
                    data.message?.includes("Unauthorized")
                  ) {
                    errorContent =
                      "인증이 만료되었습니다. 다시 로그인해주세요.";
                  } else if (
                    data.message?.includes("timeout") ||
                    data.message?.includes("시간 초과")
                  ) {
                    errorContent =
                      "처리 시간이 초과되었습니다. 요청을 단순화하거나 잠시 후 다시 시도해주세요.";
                  } else if (
                    data.message?.includes("rate limit") ||
                    data.message?.includes("제한")
                  ) {
                    errorContent =
                      "요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요.";
                  }

                  updatedMessages[streamingMsgIndex] = {
                    ...updatedMessages[streamingMsgIndex],
                    content: errorContent,
                    isLoading: false,
                    isStreaming: false,
                    isError: true,
                    timestamp: new Date().toISOString(),
                  };
                }

                return updatedMessages;
              });
              streamingMessageIdRef.current = null;
            }

            // 사용자 친화적인 토스트 메시지
            const toastMessage = data.message?.includes("401")
              ? "인증이 만료되었습니다"
              : "처리 중 오류가 발생했습니다";
            toast.error(toastMessage);
            break;

          default:
            console.log("알 수 없는 WebSocket 메시지 타입:", data.type);
        }
      } catch (error) {
        console.error("WebSocket 메시지 파싱 오류:", error);
      }
    };

    if (wsConnected) {
      addMessageListener(handleWebSocketMessage);
    }

    return () => {
      if (wsConnected) {
        removeMessageListener(handleWebSocketMessage);
      }
    };
  }, [wsConnected, addMessageListener, removeMessageListener, scrollToBottom]);

  /**
   * 스트리밍 응답 처리 함수
   */
  const handleStreamingResponse = useCallback(
    (chunk, metadata) => {
      const currentStreamingId = streamingMessageIdRef.current;

      console.log("청크 수신:", chunk, "스트리밍 ID:", currentStreamingId);

      if (!currentStreamingId) {
        console.error("스트리밍 ID가 없습니다!");
        return;
      }

      setMessages((prev) => {
        const updatedMessages = [...prev];
        const streamingMsgIndex = updatedMessages.findIndex(
          (msg) => msg.id === currentStreamingId
        );

        if (streamingMsgIndex !== -1) {
          // 기존 스트리밍 메시지 업데이트
          updatedMessages[streamingMsgIndex] = {
            ...updatedMessages[streamingMsgIndex],
            content: updatedMessages[streamingMsgIndex].content + chunk,
            isLoading: true,
            isStreaming: true,
          };
          console.log(
            "스트리밍 메시지 업데이트 성공:",
            updatedMessages[streamingMsgIndex].content
          );
        } else {
          console.error("스트리밍 메시지를 찾을 수 없음:", currentStreamingId);
        }

        return updatedMessages;
      });

      // 스크롤 조정 (사용자가 스크롤 중이 아닐 때만)
      if (!isUserScrolling) {
        scrollToBottom();
      }
    },
    [scrollToBottom, isUserScrolling]
  );

  /**
   * 스트리밍 완료 처리 함수
   */
  const handleStreamingComplete = useCallback(
    (result) => {
      const currentStreamingId = streamingMessageIdRef.current;

      console.log("스트리밍 완료:", result, "스트리밍 ID:", currentStreamingId);

      if (!currentStreamingId) {
        console.error("스트리밍 완료 처리 중 ID가 없습니다!");
        return;
      }

      setMessages((prev) => {
        const updatedMessages = [...prev];
        const streamingMsgIndex = updatedMessages.findIndex(
          (msg) => msg.id === currentStreamingId
        );

        if (streamingMsgIndex !== -1) {
          // 스트리밍 메시지 완료 처리
          updatedMessages[streamingMsgIndex] = {
            ...updatedMessages[streamingMsgIndex],
            content: result.result,
            isLoading: false,
            isStreaming: false,
            performance_metrics: result.performance_metrics,
            model_info: result.model_info,
            timestamp: new Date().toISOString(),
          };
          console.log(
            "스트리밍 완료 처리 성공:",
            updatedMessages[streamingMsgIndex].content
          );
        } else {
          console.error(
            "스트리밍 완료 처리 중 메시지를 찾을 수 없음:",
            currentStreamingId
          );
        }

        return updatedMessages;
      });

      // 스트리밍 ID 초기화
      streamingMessageIdRef.current = null;

      // 입력 활성화
      console.log("WebSocket 스트리밍 완료 - 입력 활성화");
      setCanSendMessage(true);

      // 스크롤 조정 (스트리밍 완료 시에는 항상 하단으로)
      scrollToBottom();
    },
    [scrollToBottom]
  );

  /**
   * 스트리밍 중단 함수
   */
  const handleStopGeneration = useCallback(() => {
    console.log("생성 중단 요청");

    // WebSocket 연결 종료
    if (currentWebSocketRef.current) {
      currentWebSocketRef.current.close();
      currentWebSocketRef.current = null;
    }

    // 현재 실행 중인 작업 중단
    if (currentExecutionIdRef.current) {
      // 여기서 실제 API 호출 중단 로직을 추가할 수 있습니다
      currentExecutionIdRef.current = null;
    }

    // 스트리밍 메시지 상태 업데이트
    const currentStreamingId = streamingMessageIdRef.current;
    if (currentStreamingId) {
      setMessages((prev) => {
        const updatedMessages = [...prev];
        const streamingMsgIndex = updatedMessages.findIndex(
          (msg) => msg.id === currentStreamingId
        );

        if (streamingMsgIndex !== -1) {
          updatedMessages[streamingMsgIndex] = {
            ...updatedMessages[streamingMsgIndex],
            content:
              updatedMessages[streamingMsgIndex].content +
              "\n\n[생성이 중단되었습니다]",
            isLoading: false,
            isStreaming: false,
            timestamp: new Date().toISOString(),
          };
        }

        return updatedMessages;
      });

      streamingMessageIdRef.current = null;
    }

    // 입력 가능 상태로 복원
    setCanSendMessage(true);

    // orchestration 상태 리셋
    // thinkingProcessActions가 제공되지 않으면 리셋하지 않음
    if (thinkingProcessActions) {
      thinkingProcessActions.resetOrchestration();
    }

    toast.success("생성이 중단되었습니다");
  }, [thinkingProcessActions]);

  /**
   * 입력창 높이 자동 조절
   */
  const adjustInputHeight = useCallback((value) => {
    if (!value.trim()) {
      setInputHeight(24); // 기본 높이
      return;
    }

    // 줄 수 계산 (대략적)
    const lines = value.split("\n").length;
    const charBasedLines = Math.ceil(value.length / 80); // 80자당 1줄로 추정
    const estimatedLines = Math.max(lines, charBasedLines);

    // 높이 계산 (lineHeight: 1.4, fontSize: 16px)
    let calculatedHeight;
    if (estimatedLines <= 3) {
      calculatedHeight = 24 + (estimatedLines - 1) * 22; // 기본 + 추가 줄
    } else if (estimatedLines <= 10) {
      calculatedHeight = 150 + (estimatedLines - 6) * 15; // 중간 범위
    } else {
      calculatedHeight = Math.min(400, 150 + (estimatedLines - 6) * 12); // 최대 400px
    }

    setInputHeight(Math.max(24, calculatedHeight));
  }, []);

  /**
   * 입력값 변경 처리
   */
  const handleInputChange = useCallback(
    (value) => {
      setInputValue(value);
      adjustInputHeight(value);
    },
    [adjustInputHeight]
  );

  // 사용자 입력으로부터 대화 제목 생성
  const generateConversationTitle = useCallback((userInput) => {
    const firstLine = userInput.split("\n")[0];
    const title =
      firstLine.length > 50 ? firstLine.substring(0, 47) + "..." : firstLine;
    return title.trim() || "새 대화";
  }, []);

  /**
   * 메시지 전송
   */
  const handleSendMessage = useCallback(async () => {
    console.log("🚀 메시지 전송 시작");

    if (!inputValue.trim() || !canSendMessage) {
      console.log("⚠️ 전송 조건 부족");
      return;
    }

    // 현재 대화 ID가 없고 생성 함수가 있으면 새 대화 생성
    let conversationIdToUse = conversationId;
    if (
      !conversationIdToUse &&
      createConversationFn &&
      setCurrentConversationFn
    ) {
      console.log(
        "🔍 [DEBUG] 새 대화 생성 시작 - 제목:",
        generateConversationTitle(inputValue)
      );

      try {
        const newTitle = generateConversationTitle(inputValue);
        const newConversation = await createConversationFn(newTitle);
        console.log("🔍 [DEBUG] 새 대화 생성 완료:", newConversation);

        conversationIdToUse = newConversation.id;
        setCurrentConversationFn(conversationIdToUse);

        // ConversationContext에도 새 대화 추가 (실시간 UI 업데이트)
        if (addConversationFn) {
          console.log(
            "🎉 [DEBUG] ConversationContext에 새 대화 추가:",
            newConversation
          );
          addConversationFn(newConversation);
        }

        // 상태 업데이트 대기
        await new Promise((resolve) => setTimeout(resolve, 100));
      } catch (error) {
        console.error("🔍 [DEBUG] 대화 생성 실패:", error);
      }
    }

    // 입력 비활성화
    console.log("입력 비활성화");
    setCanSendMessage(false);

    const userMessage = {
      id: "user-" + Date.now(),
      type: "user",
      content: inputValue.trim(),
      timestamp: new Date().toISOString(),
    };

    // 스트리밍 메시지 ID 생성
    const streamMsgId = "streaming-" + Date.now();
    streamingMessageIdRef.current = streamMsgId;

    console.log("새 스트리밍 메시지 ID 생성:", streamMsgId);

    // 스트리밍 응답을 위한 초기 메시지
    const streamingMessage = {
      id: streamMsgId,
      type: "assistant",
      content: "",
      timestamp: new Date().toISOString(),
      isLoading: true,
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, streamingMessage]);
    setInputValue("");
    setInputHeight(24); // 입력창 높이 초기화

    // 기존 메시지 + 현재 사용자 메시지를 포함한 대화 히스토리 생성
    const allMessages = [...messages, userMessage];
    const chatHistory = allMessages
      .filter((msg) => !msg.isLoading && !msg.isError && !msg.isStreaming)
      .map((msg) => ({
        role: msg.type === "user" ? "user" : "assistant",
        content: msg.content,
      }));

    // 최대 대화 기억 설정 (최근 50개 메시지로 최대 메모리 유지)
    const maxHistoryLength = 50;
    const trimmedChatHistory = chatHistory.slice(-maxHistoryLength);

    console.log("대화 히스토리 생성:", {
      totalMessages: allMessages.length,
      fullHistoryLength: chatHistory.length,
      trimmedHistoryLength: trimmedChatHistory.length,
      maxHistoryLength: maxHistoryLength,
      recentHistory: trimmedChatHistory.slice(-6), // 최근 6개만 로그에 표시
    });

    try {
      // 프롬프트 카드 정보 추가 - 활성화된 카드만 필터링하고 백엔드 형식에 맞게 변환
      const safePromptCards = Array.isArray(promptCards) ? promptCards : [];
      const activePromptCards = safePromptCards
        .filter((card) => card.isActive !== false && card.enabled !== false)
        .map((card) => ({
          promptId: card.promptId || card.prompt_id,
          title: card.title || "Untitled",
          prompt_text: card.prompt_text || card.content || "",
          tags: card.tags || [],
          isActive: card.isActive !== false,
          stepOrder: card.stepOrder || 0,
        }))
        .filter((card) => card.prompt_text.trim()) // 프롬프트 내용이 있는 것만
        .sort((a, b) => (a.stepOrder || 0) - (b.stepOrder || 0)); // stepOrder로 정렬

      console.log("대화 전송 데이터 확인:", {
        messageContent: userMessage.content,
        chatHistoryLength: trimmedChatHistory.length,
        promptCardsCount: activePromptCards.length,
        chatHistory: trimmedChatHistory,
        promptCards: activePromptCards.map((card) => ({
          id: card.promptId,
          title: card.title,
          contentLength: card.prompt_text.length,
          stepOrder: card.stepOrder,
          hasContent: !!card.prompt_text.trim(),
        })),
      });

      // WebSocket 연결 확인 및 실시간 스트리밍 시도
      if (wsConnected) {
        console.log("WebSocket을 통한 실시간 스트리밍 시작");
        console.log("🔍 [DEBUG] 스트리밍 매개변수 상세 확인:", {
          userId: user?.id,
          userInput: userMessage.content,
          conversationId: conversationIdToUse,
          userSub: user?.id,
          historyLength: trimmedChatHistory.length,
          promptCardsCount: promptCards?.length || 0,
          selectedModel,
        });

        const success = wsStartStreaming(
          userMessage.content,
          trimmedChatHistory,
          activePromptCards,
          selectedModel,
          conversationIdToUse, // 새로 생성된 conversationId 사용
          user?.id // Add userSub from AuthContext
        );

        if (success) {
          // WebSocket 스트리밍 성공, 나머지는 리스너에서 처리
          console.log(
            "🎉 [DEBUG] WebSocket 스트리밍 요청 성공 - conversationId:",
            conversationIdToUse
          );
          return;
        } else {
          console.log("🚨 [DEBUG] WebSocket 전송 실패, SSE 폴백 모드로 전환");
        }
      } else {
        console.log("WebSocket 미연결, SSE 모드 사용");
      }

      // SSE 폴백 모드로 전환
      console.log("SSE 모드로 대화 처리");

      // 🎯 직접 API 호출로 변경 (오케스트레이션 의존성 제거)
      const apiUrl =
        "https://5navjh90o6.execute-api.ap-northeast-2.amazonaws.com/prod";
      const endpoint = `${apiUrl}/projects/${
        projectId || "default"
      }/generate/stream`;

      const requestData = {
        userInput: userMessage.content,
        chat_history: trimmedChatHistory,
        prompt_cards: activePromptCards,
        modelId: selectedModel,
        useKnowledgeBase: true,
      };

      console.log("🚀 직접 API 호출:", { endpoint, requestData });

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

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          ...authHeaders,
        },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      // 스트리밍 응답 처리
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
                if (eventData.result) {
                  fullResponse = eventData.result;
                  handleStreamingResponse(eventData.result);
                }
              } catch (parseError) {
                console.error("스트리밍 데이터 파싱 오류:", parseError);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
      }

      // 완료 콜백 호출
      if (fullResponse) {
        handleStreamingComplete({ result: fullResponse });
      } else {
        throw new Error("스트리밍 응답에서 결과를 찾을 수 없습니다");
      }
    } catch (error) {
      console.error("메시지 전송 실패:", error);

      // API 오류 처리 위임
      const { userMessage: errorUserMessage, shouldRedirect } =
        await handleAPIError(error);

      // 인증 오류로 리다이렉트가 필요한 경우
      if (shouldRedirect) {
        return;
      }

      const errorMessage = {
        id: "error-" + Date.now(),
        type: "assistant",
        content: errorUserMessage,
        timestamp: new Date().toISOString(),
        isError: true,
        errorDetails: {
          message: error.message,
          status: error.response?.status,
          code: error.code,
        },
      };

      setMessages((prev) => {
        // 스트리밍 메시지를 찾아 제거
        const currentStreamingId = streamingMessageIdRef.current;
        const filteredMessages = prev.filter(
          (msg) => msg.id !== currentStreamingId
        );
        return [...filteredMessages, errorMessage];
      });

      streamingMessageIdRef.current = null;

      // 오류 발생 시도 입력 활성화
      setCanSendMessage(true);
    }

    // 전체 전송 과정 완료 후 입력 활성화 (보험용)
    setCanSendMessage(true);
  }, [
    inputValue,
    conversationId,
    createConversationFn,
    setCurrentConversationFn,
    addConversationFn,
    generateConversationTitle,
    executeOrchestration,
    handleStreamingResponse,
    handleStreamingComplete,
    messages,
    wsConnected,
    wsStartStreaming,
    selectedModel,
    user?.id,
  ]);

  /**
   * Enter 키로 전송
   */
  const handleKeyPress = useCallback(
    (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSendMessage();
      }
    },
    [handleSendMessage]
  );

  /**
   * 메시지 복사
   */
  const handleCopyMessage = useCallback(async (content, messageId) => {
    try {
      await navigator.clipboard.writeText(content);
      toast.success("클립보드에 복사되었습니다!");
      setCopiedMessage(messageId);
      setTimeout(() => setCopiedMessage(null), 2000);
    } catch (error) {
      console.error("복사 실패:", error);
      toast.error("복사에 실패했습니다.");
    }
  }, []);

  /**
   * 개별 제목 복사
   */
  const handleCopyTitle = useCallback(async (title, messageId, index) => {
    try {
      await navigator.clipboard.writeText(title);
      toast.success("복사되었습니다!");
      setCopiedMessage(`${messageId}_title_${index}`);
      setTimeout(() => setCopiedMessage(null), 2000);
    } catch (error) {
      console.error("복사 실패:", error);
      toast.error("복사에 실패했습니다.");
    }
  }, []);

  /**
   * 채팅 초기화
   */
  const resetChat = useCallback(() => {
    console.log("🔍 [DEBUG] useChat 완전 초기화 실행");
    setMessages([]);
    setInputValue("");
    setCopiedMessage(null);
    setCanSendMessage(true);
    setInputHeight(24);
    setIsUserScrolling(false);
    streamingMessageIdRef.current = null;
    currentWebSocketRef.current = null;
    currentExecutionIdRef.current = null;
    // thinkingProcessActions가 제공되지 않으면 리셋하지 않음
    if (thinkingProcessActions) {
      thinkingProcessActions.resetOrchestration();
    }
  }, [thinkingProcessActions]);

  // conversationId가 null로 변경될 때 자동으로 초기화
  useEffect(() => {
    if (conversationId === null) {
      console.log(
        "🔍 [DEBUG] conversationId가 null로 변경됨 - 채팅 완전 초기화"
      );
      resetChat();
    }
  }, [conversationId, resetChat]);

  return {
    messages,
    inputValue,
    setInputValue,
    handleInputChange, // 새로운 입력 핸들러
    copiedMessage,
    // isGenerating, // 🗑️ 제거: canSendMessage로 대체
    // isStreaming, // 🗑️ 제거: 필요한 곳에서 개별 관리
    canSendMessage,
    streamingMessageId: streamingMessageIdRef.current,
    messagesEndRef,
    inputRef,
    inputHeight, // 동적 높이
    handleSendMessage,
    handleStopGeneration,
    handleKeyPress,
    handleCopyMessage,
    handleCopyTitle,
    resetChat,
    scrollToBottom,
    // WebSocket 상태 추가
    wsConnected,
    wsConnecting,
    wsError,
    // 스크롤 관련 추가
    scrollContainerRef,
    handleScroll,
    isUserScrolling,
    // 모델 선택 관련 추가
    selectedModel,
    setSelectedModel,
    generateConversationTitle,
  };
};

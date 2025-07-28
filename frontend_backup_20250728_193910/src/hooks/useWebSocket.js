import { useState, useEffect, useRef, useCallback } from "react";

/**
 * WebSocket 실시간 스트리밍을 위한 커스텀 훅
 */
export const useWebSocket = (projectId) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState(null);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  // WebSocket URL (환경변수나 실제 배포된 URL로 설정)
  const getWebSocketUrl = useCallback(async () => {
    const wsUrl =
      process.env.REACT_APP_WS_URL ||
      "wss://your-websocket-api.execute-api.us-east-1.amazonaws.com/prod";
    
    // URL 형식 검증 및 정규화
    if (!wsUrl.startsWith("wss://") && !wsUrl.startsWith("ws://")) {
      console.error("잘못된 WebSocket URL 형식:", wsUrl);
      return null;
    }
    
    // 끝에 슬래시 제거
    let normalizedUrl = wsUrl.replace(/\/$/, "");
    
    // 개발 모드에서 인증 스킵
    if (process.env.REACT_APP_SKIP_AUTH === 'true') {
      console.log("🔓 개발 모드: WebSocket 인증 스킵");
    } else {
      // 인증 토큰을 쿼리 파라미터로 추가
      try {
        const { fetchAuthSession } = await import('aws-amplify/auth');
        const session = await fetchAuthSession();
        const token = session?.tokens?.idToken?.toString();
        
        if (token) {
          // URL에 토큰을 쿼리 파라미터로 추가
          normalizedUrl += `?token=${encodeURIComponent(token)}`;
          console.log("✅ WebSocket URL에 인증 토큰 추가됨");
        } else {
          console.log("⚠️ 인증 토큰이 없음 - 공개 WebSocket 연결 시도");
        }
      } catch (authError) {
        console.log("📝 인증 토큰 가져오기 실패:", authError.message);
      }
    }
    
    console.log("WebSocket URL 확인:", normalizedUrl.replace(/token=[^&]+/, 'token=***'));
    console.log("환경변수 REACT_APP_WS_URL:", process.env.REACT_APP_WS_URL);
    
    return normalizedUrl;
  }, []);

  // WebSocket 연결
  const connect = useCallback(async () => {
    // 이미 연결 중이거나 연결된 경우 중복 연결 방지
    if (wsRef.current?.readyState === WebSocket.OPEN || 
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.log("이미 연결된 WebSocket이 있습니다 (readyState:", wsRef.current.readyState, ")");
      return;
    }

    // 이전 연결이 있다면 정리
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnecting(true);
    setError(null);

    try {
      const wsUrl = await getWebSocketUrl();
      
      if (!wsUrl) {
        setError("유효하지 않은 WebSocket URL");
        setIsConnecting(false);
        return;
      }

      console.log("WebSocket 연결 시도:", wsUrl);
      console.log("브라우저 WebSocket 지원:", !!window.WebSocket);

      // 연결 시도 시간 기록
      window.wsConnectStart = Date.now();

      wsRef.current = new WebSocket(wsUrl);

      // 연결 상태 모니터링
      const connectionTimeout = setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.CONNECTING) {
          console.error("WebSocket 연결 시간 초과");
          wsRef.current.close();
          setError("연결 시간이 초과되었습니다");
          setIsConnecting(false);
        }
      }, 10000); // 10초 타임아웃

      wsRef.current.onopen = (event) => {
        clearTimeout(connectionTimeout);
        console.log("🟢 WebSocket 연결 성공!");
        console.log("- Event:", event);
        console.log("- URL:", wsRef.current?.url);
        console.log("- Protocol:", wsRef.current?.protocol);
        console.log("- Extensions:", wsRef.current?.extensions);
        setIsConnected(true);
        setIsConnecting(false);
        setError(null);
        reconnectAttempts.current = 0;
      };

      wsRef.current.onclose = (event) => {
        clearTimeout(connectionTimeout);
        const connectionDuration = Date.now() - (window.wsConnectStart || 0);
        
        console.log("🔴 WebSocket 연결 종료:");
        console.log("- Code:", event.code);
        console.log("- Reason:", event.reason || "(no reason provided)");
        console.log("- WasClean:", event.wasClean);
        console.log("- Connection duration:", connectionDuration + "ms");
        
        setIsConnected(false);
        setIsConnecting(false);

        // 즉시 종료된 경우 (500ms 이내) - 서버 문제
        if (connectionDuration < 500) {
          console.error("⚠️ WebSocket이 즉시 종료됨 - 서버 문제 가능성");
          
          // 특정 에러 코드에 따른 세분화된 에러 메시지
          let errorMessage = "서버 연결에 실패했습니다.";
          switch(event.code) {
            case 1006:
              errorMessage = "비정상적인 연결 종료 (네트워크 문제 가능성)";
              break;
            case 1002:
              errorMessage = "프로토콜 오류";
              break;
            case 1003:
              errorMessage = "지원하지 않는 데이터 타입";
              break;
            case 1011:
              errorMessage = "서버 내부 오류";
              break;
            case 1001:
              errorMessage = "서버가 종료되었습니다";
              break;
            case 1012:
              errorMessage = "서버 재시작 중입니다";
              break;
            case 1013:
              errorMessage = "나중에 다시 시도해주세요";
              break;
            case 1014:
              errorMessage = "잘못된 게이트웨이";
              break;
            case 1015:
              errorMessage = "TLS 연결 실패";
              break;
          }
          
          setError(errorMessage);
          return;
        }

        // 자동 재연결 (정상 종료가 아닌 경우)
        if (
          event.code !== 1000 &&
          reconnectAttempts.current < maxReconnectAttempts
        ) {
          const delay = Math.min(
            1000 * Math.pow(2, reconnectAttempts.current),
            30000
          );
          console.log(
            `🔄 ${delay}ms 후 재연결 시도 (${
              reconnectAttempts.current + 1
            }/${maxReconnectAttempts})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        } else if (reconnectAttempts.current >= maxReconnectAttempts) {
          setError("최대 재연결 시도 횟수에 도달했습니다.");
        }
      };

      wsRef.current.onerror = (error) => {
        clearTimeout(connectionTimeout);
        console.error("💥 WebSocket 오류:", error);
        console.log("- ReadyState:", wsRef.current?.readyState);
        console.log("- URL:", wsRef.current?.url);
        setError("WebSocket 연결 오류가 발생했습니다");
        setIsConnecting(false);
      };

    } catch (err) {
      console.error("💥 WebSocket 생성 실패:", err);
      setError("WebSocket 연결에 실패했습니다: " + err.message);
      setIsConnecting(false);
    }
  }, [getWebSocketUrl]);

  // WebSocket 연결 해제
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close(1000, "Manual disconnect");
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsConnecting(false);
    reconnectAttempts.current = 0;
  }, []);

  // 메시지 전송
  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
      return true;
    } else {
      console.error("WebSocket이 연결되지 않았습니다");
      setError("WebSocket 연결이 필요합니다");
      return false;
    }
  }, []);

  // 스트리밍 요청
  const startStreaming = useCallback(
    (userInput, chatHistory = [], promptCards = [], modelId = null, conversationId = null, userSub = null) => {
      if (!isConnected) {
        setError("WebSocket 연결이 필요합니다");
        return false;
      }

      const message = {
        action: "stream",
        projectId,
        userInput,
        chat_history: chatHistory,
        prompt_cards: promptCards,
        modelId: modelId,
        conversationId: conversationId,
        userSub: userSub,
        useKnowledgeBase: true, // Enhanced Agent System 활성화
      };

      console.log('🔍 [DEBUG] WebSocket 메시지 전송 상세:', {
        action: message.action,
        projectId: message.projectId,
        inputLength: userInput.length,
        historyLength: chatHistory.length,
        promptCardsCount: promptCards.length,
        conversationId: message.conversationId,
        conversationIdType: typeof message.conversationId,
        conversationIdValue: message.conversationId,
        isConversationIdNull: message.conversationId === null,
        isConversationIdUndefined: message.conversationId === undefined,
        userSub: message.userSub,
        fullMessage: JSON.stringify(message)
      });

      return sendMessage(message);
    },
    [isConnected, projectId, sendMessage]
  );

  // 메시지 리스너 등록
  const addMessageListener = useCallback((listener) => {
    if (wsRef.current) {
      wsRef.current.addEventListener("message", listener);
    }
  }, []);

  // 메시지 리스너 제거
  const removeMessageListener = useCallback((listener) => {
    if (wsRef.current) {
      wsRef.current.removeEventListener("message", listener);
    }
  }, []);

  // 컴포넌트 마운트 시 연결, 언마운트 시 해제
  useEffect(() => {
    // 초기 연결 지연을 통해 React strict mode 이슈 회피
    const timer = setTimeout(() => {
      connect();
    }, 100);
    
    return () => {
      clearTimeout(timer);
      disconnect();
    };
  }, []); // 의존성 배열을 빈 배열로 변경

  // projectId 변경 시 재연결 (이전 값과 비교하여 실제 변경시에만)
  const prevProjectIdRef = useRef(projectId);
  useEffect(() => {
    if (prevProjectIdRef.current !== projectId && isConnected && projectId) {
      console.log('ProjectId 변경됨, 재연결 중:', prevProjectIdRef.current, '->', projectId);
      disconnect();
      setTimeout(connect, 200);
    }
    prevProjectIdRef.current = projectId;
  }, [projectId, isConnected]); // connect, disconnect 의존성 제거

  return {
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    sendMessage,
    startStreaming,
    addMessageListener,
    removeMessageListener,
  };
};

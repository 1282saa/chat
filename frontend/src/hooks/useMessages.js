import { useState, useEffect, useCallback } from "react";
import { conversationAPI } from "../services/api";

/**
 * 특정 대화의 메시지 관리를 위한 커스텀 훅
 * 페이지네이션과 실시간 메시지 추가 지원
 */
export const useMessages = (conversationId) => {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [nextCursor, setNextCursor] = useState(null);

  // 메시지 로드
  const loadMessages = useCallback(
    async (reset = false) => {
      if (!conversationId || loading) {
        console.log("useMessages - 메시지 로드 중단:", {
          conversationId,
          loading,
        });
        return;
      }

      console.log("useMessages - 메시지 로드 시작:", {
        conversationId,
        reset,
        cursor: reset ? null : nextCursor,
        currentMessagesCount: messages.length,
      });

      setLoading(true);
      setError(null);

      try {
        console.log("🔍 [DEBUG] useMessages - 세션 기반 메시지 로드:", {
          conversationId,
          reset,
          currentMessagesCount: messages.length,
        });

        // 세션 스토리지에서 메시지 불러오기
        let conversationMessages = [];

        if (conversationId) {
          const conversationKey = `conversation_${conversationId}`;
          const conversationData = sessionStorage.getItem(conversationKey);

          if (conversationData) {
            try {
              const conversation = JSON.parse(conversationData);
              conversationMessages = conversation.messages || [];
              console.log(
                "🔍 [DEBUG] 세션에서 메시지 로드 완료:",
                conversationMessages.length
              );
            } catch (parseError) {
              console.warn("대화 데이터 파싱 실패:", parseError);
            }
          } else {
            console.log(
              "🔍 [DEBUG] 세션에서 대화를 찾을 수 없음:",
              conversationId
            );
          }
        }

        console.log("useMessages - 세션 데이터:", {
          conversationId,
          messagesReceived: conversationMessages.length,
          hasMore: false,
          reset,
        });

        if (reset) {
          setMessages(conversationMessages);
        } else {
          // 이전 메시지들을 앞에 추가 (페이지네이션)
          setMessages((prev) => [...conversationMessages, ...prev]);
        }

        setHasMore(false); // 세션 기반에서는 페이징 불필요
        setNextCursor(null);
      } catch (error) {
        console.error("세션 메시지 로드 실패:", error);

        if (reset) {
          setMessages([]);
          setHasMore(false);
          setNextCursor(null);
        }
      } finally {
        setLoading(false);
      }
    },
    [conversationId, loading, nextCursor, messages.length]
  );

  // 새 메시지 추가 (실시간)
  const addMessage = useCallback((message) => {
    const newMessage = {
      id: message.timestamp || new Date().toISOString(),
      role: message.role,
      content: message.content,
      tokenCount: message.tokenCount || 0,
      timestamp: message.timestamp || new Date().toISOString(),
    };

    setMessages((prev) => [...prev, newMessage]);
    return newMessage;
  }, []);

  // 메시지 업데이트 (스트리밍 중 내용 업데이트)
  const updateMessage = useCallback((messageId, updates) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === messageId ? { ...msg, ...updates } : msg))
    );
  }, []);

  // 메시지 삭제
  const removeMessage = useCallback((messageId) => {
    setMessages((prev) => prev.filter((msg) => msg.id !== messageId));
  }, []);

  // 이전 메시지 로드 (스크롤 최상단에서)
  const loadPreviousMessages = useCallback(() => {
    if (hasMore && !loading) {
      return loadMessages(false);
    }
    return Promise.resolve();
  }, [hasMore, loading, loadMessages]);

  // 메시지 초기화 (새 대화 시작시)
  const clearMessages = useCallback(() => {
    setMessages([]);
    setHasMore(true);
    setNextCursor(null);
    setError(null);
  }, []);

  // conversationId 변경시 메시지 로드
  useEffect(() => {
    console.log("🔍 [DEBUG] useMessages - conversationId 변경 감지:", {
      conversationId,
      conversationIdType: typeof conversationId,
      isConversationIdNull: conversationId === null,
      isConversationIdUndefined: conversationId === undefined,
      previousConversationId: conversationId, // 이전 값을 추적하기 어려우므로 현재 값만 표시
    });

    if (conversationId) {
      console.log(
        "🔍 [DEBUG] useMessages - 메시지 클리어 및 로드 시작:",
        conversationId
      );
      clearMessages();
      loadMessages(true);
    } else {
      console.log(
        "🔍 [DEBUG] useMessages - conversationId가 null/undefined, 메시지 클리어"
      );
      clearMessages();
    }
  }, [conversationId]);

  return {
    messages,
    loading,
    error,
    hasMore,
    addMessage,
    updateMessage,
    removeMessage,
    loadPreviousMessages,
    clearMessages,
    refresh: () => loadMessages(true),
  };
};

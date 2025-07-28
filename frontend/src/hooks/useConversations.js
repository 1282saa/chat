import { useState, useEffect, useCallback } from "react";
import { conversationAPI } from "../services/api";

/**
 * 대화 목록 관리를 위한 커스텀 훅
 * 무한 스크롤과 실시간 업데이트 지원
 */
export const useConversations = () => {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasMore, setHasMore] = useState(true);
  const [nextCursor, setNextCursor] = useState(null);

  // 대화 목록 초기 로드
  const loadConversations = useCallback(
    async (reset = false) => {
      if (loading) return;

      setLoading(true);
      setError(null);

      try {
        console.log("🔍 [DEBUG] useConversations - 세션 기반 대화 목록 로드");

        // 세션 스토리지에서 대화 목록 불러오기
        const conversations = [];
        for (let i = 0; i < sessionStorage.length; i++) {
          const key = sessionStorage.key(i);
          if (key && key.startsWith("conversation_")) {
            try {
              const conversationData = JSON.parse(sessionStorage.getItem(key));
              conversations.push({
                id: conversationData.id,
                title: conversationData.title,
                startedAt: conversationData.startedAt,
                lastActivityAt:
                  conversationData.lastActivityAt || conversationData.startedAt,
                tokenSum: conversationData.messages?.length || 0,
              });
            } catch (parseError) {
              console.warn("대화 데이터 파싱 실패:", key, parseError);
            }
          }
        }

        // 최근 순으로 정렬
        conversations.sort(
          (a, b) => new Date(b.lastActivityAt) - new Date(a.lastActivityAt)
        );

        if (reset) {
          setConversations(conversations);
        } else {
          setConversations((prev) => [...prev, ...conversations]);
        }

        setHasMore(false); // 세션 기반에서는 페이징 불필요
        setNextCursor(null);
      } catch (error) {
        console.error("세션 대화 목록 조회 실패:", error);

        if (reset) {
          setConversations([]);
          setHasMore(false);
          setNextCursor(null);
        }
      } finally {
        setLoading(false);
      }
    },
    [loading, nextCursor]
  );

  // 새 대화 생성
  const createConversation = useCallback(async (title) => {
    console.log("🔍 [DEBUG] createConversation 호출:", { title });

    try {
      console.log("🔍 [DEBUG] 세션 기반 대화 생성:", title);

      // 세션 기반 대화 생성
      const conversationId = `session_${Date.now()}_${Math.random()
        .toString(36)
        .substr(2, 9)}`;
      const now = new Date().toISOString();

      const newConversation = {
        id: conversationId,
        title: title || "새 대화",
        startedAt: now,
        lastActivityAt: now,
        tokenSum: 0,
        messages: [],
      };

      console.log("🔍 [DEBUG] 새 대화 객체 생성:", newConversation);

      // 세션 스토리지에 저장
      sessionStorage.setItem(
        `conversation_${conversationId}`,
        JSON.stringify(newConversation)
      );

      // 새 대화를 목록 맨 앞에 추가
      setConversations((prev) => {
        console.log("🔍 [DEBUG] 대화 목록 업데이트 - 이전:", prev.length);
        const updated = [newConversation, ...prev];
        console.log("🔍 [DEBUG] 대화 목록 업데이트 - 이후:", updated.length);
        return updated;
      });

      return newConversation;
    } catch (error) {
      console.error("세션 대화 생성 실패:", error);
      throw error;
    }
  }, []);

  // 대화 업데이트 (마지막 활동 시간, 제목 등)
  const updateConversation = useCallback(async (conversationId, updates) => {
    try {
      // API 호출로 실제 업데이트 시도
      console.log("대화 업데이트 API 호출:", conversationId, updates);
      await conversationAPI.updateConversation(conversationId, updates);
      console.log("대화 업데이트 API 성공");
    } catch (err) {
      console.warn("대화 업데이트 API 실패, 로컬에서만 업데이트:", err);
      // API 실패 시에도 로컬에서는 업데이트 진행
    }

    // API 성공/실패 관계없이 로컬 상태 업데이트
    setConversations((prev) =>
      prev.map((conv) =>
        conv.id === conversationId
          ? { ...conv, ...updates, lastActivityAt: new Date().toISOString() }
          : conv
      )
    );
  }, []);

  // 대화 삭제
  const deleteConversation = useCallback(async (conversationId) => {
    try {
      // API 호출로 실제 삭제 시도
      await conversationAPI.deleteConversation(conversationId);
      console.log("API 삭제 성공:", conversationId);
    } catch (err) {
      console.warn("API 삭제 실패, 로컬에서만 삭제:", err);
      // API 실패 시에도 로컬에서는 삭제 진행
    }

    // API 성공/실패 관계없이 UI에서 제거
    setConversations((prev) =>
      prev.filter((conv) => conv.id !== conversationId)
    );

    return true;
  }, []);

  // 대화 삭제 (UI에서만 제거, 실제 삭제는 별도 구현)
  const removeConversation = useCallback((conversationId) => {
    setConversations((prev) =>
      prev.filter((conv) => conv.id !== conversationId)
    );
  }, []);

  // 다음 페이지 로드 (무한 스크롤)
  const loadMore = useCallback(() => {
    if (hasMore && !loading) {
      loadConversations(false);
    }
  }, [hasMore, loading, loadConversations]);

  // 새로고침
  const refresh = useCallback(() => {
    loadConversations(true);
  }, [loadConversations]);

  // 초기 로드
  useEffect(() => {
    loadConversations(true);
  }, []);

  return {
    conversations,
    loading,
    error,
    hasMore,
    loadMore,
    refresh,
    createConversation,
    updateConversation,
    deleteConversation,
    removeConversation,
  };
};

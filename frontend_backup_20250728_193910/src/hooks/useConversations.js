import { useState, useEffect, useCallback } from 'react';
import { conversationAPI, mockConversations } from '../services/api';

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
  const loadConversations = useCallback(async (reset = false) => {
    if (loading) return;
    
    setLoading(true);
    setError(null);

    try {
      const cursor = reset ? null : nextCursor;
      const response = await conversationAPI.getConversations(cursor);
      
      if (reset) {
        setConversations(response.conversations);
      } else {
        setConversations(prev => [...prev, ...response.conversations]);
      }
      
      setHasMore(response.hasMore);
      setNextCursor(response.nextCursor);
      
    } catch (err) {
      console.error('대화 목록 로드 실패:', err);
      console.error('Error details:', {
        message: err.message,
        status: err.response?.status,
        data: err.response?.data,
        config: err.config
      });
      
      // 상세한 에러 메시지 제공
      let errorMessage = '대화 목록을 불러오는데 실패했습니다.';
      if (err.code === 'ERR_NETWORK') {
        errorMessage = '네트워크 연결을 확인해주세요.';
      } else if (err.response?.status === 403) {
        errorMessage = '접근 권한이 없습니다.';
      } else if (err.response?.status >= 500) {
        errorMessage = '서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
      }
      
      setError(errorMessage);
      
      // API 실패시 mock 데이터로 fallback
      if (reset) {
        console.log('API 실패, mock 데이터 사용');
        setConversations(mockConversations);
        setHasMore(false);
        setNextCursor(null);
      }
    } finally {
      setLoading(false);
    }
  }, [loading, nextCursor]);

  // 새 대화 생성
  const createConversation = useCallback(async (title) => {
    console.log("🔍 [DEBUG] createConversation 호출:", { title });
    
    try {
      console.log("🔍 [DEBUG] API 호출 시도:", title);
      const response = await conversationAPI.createConversation(title);
      console.log("🔍 [DEBUG] API 응답:", response);
      
      const newConversation = {
        id: response.conversationId,
        title: response.title,
        startedAt: response.startedAt,
        lastActivityAt: response.lastActivityAt,
        tokenSum: 0
      };
      
      console.log("🔍 [DEBUG] 새 대화 객체 생성:", newConversation);
      
      // 새 대화를 목록 맨 앞에 추가
      setConversations(prev => {
        console.log("🔍 [DEBUG] 대화 목록 업데이트 - 이전:", prev.length, "새로 추가:", newConversation.id);
        console.log("🔍 [DEBUG] 이전 대화 목록:", prev.map(c => ({id: c.id, title: c.title})));
        const updated = [newConversation, ...prev];
        console.log("🔍 [DEBUG] 대화 목록 업데이트 - 이후:", updated.length);
        console.log("🔍 [DEBUG] 업데이트된 대화 목록:", updated.map(c => ({id: c.id, title: c.title})));
        return updated;
      });
      
      return newConversation;
    } catch (err) {
      console.error('🔍 [DEBUG] 대화 생성 API 실패:', err);
      
      // API 실패시 mock 데이터로 fallback
      const mockConversation = {
        id: Date.now().toString(),
        title: title || 'New Conversation',
        startedAt: new Date().toISOString(),
        lastActivityAt: new Date().toISOString(),
        tokenSum: 0
      };
      
      console.log("🔍 [DEBUG] Mock 대화 생성:", mockConversation);
      
      setConversations(prev => {
        console.log("🔍 [DEBUG] Mock 대화 목록 업데이트 - 이전:", prev.length);
        const updated = [mockConversation, ...prev];
        console.log("🔍 [DEBUG] Mock 대화 목록 업데이트 - 이후:", updated.length);
        return updated;
      });
      
      return mockConversation;
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
    setConversations(prev => 
      prev.map(conv => 
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
      console.log('API 삭제 성공:', conversationId);
    } catch (err) {
      console.warn('API 삭제 실패, 로컬에서만 삭제:', err);
      // API 실패 시에도 로컬에서는 삭제 진행
    }
    
    // API 성공/실패 관계없이 UI에서 제거
    setConversations(prev => prev.filter(conv => conv.id !== conversationId));
    
    return true;
  }, []);

  // 대화 삭제 (UI에서만 제거, 실제 삭제는 별도 구현)
  const removeConversation = useCallback((conversationId) => {
    setConversations(prev => prev.filter(conv => conv.id !== conversationId));
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
    removeConversation
  };
};
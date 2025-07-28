import React, { createContext, useContext, useReducer, useEffect, useMemo } from "react";
import { useAuth } from "./AuthContext";
import { conversationAPI } from "../services/api";

// 대화 상태 관리를 위한 Context
const ConversationContext = createContext();

// 초기 상태
const initialState = {
  currentConversationId: null,
  conversations: [],
  currentMessages: [],
  isLoading: false,
  error: null,
  drawerOpen: false,
};

// 액션 타입 정의
const ActionTypes = {
  SET_CURRENT_CONVERSATION: "SET_CURRENT_CONVERSATION",
  SET_CONVERSATIONS: "SET_CONVERSATIONS",
  ADD_CONVERSATION: "ADD_CONVERSATION",
  UPDATE_CONVERSATION: "UPDATE_CONVERSATION",
  SET_MESSAGES: "SET_MESSAGES",
  ADD_MESSAGE: "ADD_MESSAGE",
  UPDATE_MESSAGE: "UPDATE_MESSAGE",
  SET_LOADING: "SET_LOADING",
  SET_ERROR: "SET_ERROR",
  TOGGLE_DRAWER: "TOGGLE_DRAWER",
  CLEAR_STATE: "CLEAR_STATE",
};

// 리듀서 함수
const conversationReducer = (state, action) => {
  switch (action.type) {
    case ActionTypes.SET_CURRENT_CONVERSATION:
      return {
        ...state,
        currentConversationId: action.payload,
        currentMessages: [], // 새 대화 선택시 메시지 초기화
      };

    case ActionTypes.SET_CONVERSATIONS:
      return {
        ...state,
        conversations: action.payload,
      };

    case ActionTypes.ADD_CONVERSATION:
      return {
        ...state,
        conversations: [action.payload, ...state.conversations],
      };

    case ActionTypes.UPDATE_CONVERSATION:
      return {
        ...state,
        conversations: state.conversations.map((conv) =>
          conv.id === action.payload.id
            ? { ...conv, ...action.payload.updates }
            : conv
        ),
      };

    case ActionTypes.SET_MESSAGES:
      return {
        ...state,
        currentMessages: action.payload,
      };

    case ActionTypes.ADD_MESSAGE:
      return {
        ...state,
        currentMessages: [...state.currentMessages, action.payload],
      };

    case ActionTypes.UPDATE_MESSAGE:
      return {
        ...state,
        currentMessages: state.currentMessages.map((msg) =>
          msg.id === action.payload.id
            ? { ...msg, ...action.payload.updates }
            : msg
        ),
      };

    case ActionTypes.SET_LOADING:
      return {
        ...state,
        isLoading: action.payload,
      };

    case ActionTypes.SET_ERROR:
      return {
        ...state,
        error: action.payload,
      };

    case ActionTypes.TOGGLE_DRAWER:
      return {
        ...state,
        drawerOpen:
          action.payload !== undefined ? action.payload : !state.drawerOpen,
      };

    case ActionTypes.CLEAR_STATE:
      return initialState;

    default:
      return state;
  }
};

// Provider 컴포넌트
export const ConversationProvider = ({ children }) => {
  const [state, dispatch] = useReducer(conversationReducer, initialState);
  const { user } = useAuth();

  // 현재 대화 변경
  const setCurrentConversation = (conversationId) => {
    console.log("🔍 [DEBUG] ConversationContext - 대화 변경 요청:", {
      previousConversationId: state.currentConversationId,
      newConversationId: conversationId,
      isChanged: state.currentConversationId !== conversationId,
      conversationIdType: typeof conversationId,
      isConversationIdNull: conversationId === null,
      isConversationIdUndefined: conversationId === undefined,
    });

    dispatch({
      type: ActionTypes.SET_CURRENT_CONVERSATION,
      payload: conversationId,
    });

    console.log(
      "🔍 [DEBUG] ConversationContext - 대화 변경 dispatch 완료:",
      conversationId
    );
  };

  // 대화 목록 설정
  const setConversations = (conversations) => {
    dispatch({
      type: ActionTypes.SET_CONVERSATIONS,
      payload: conversations,
    });
  };

  // 새 대화 추가
  const addConversation = (conversation) => {
    dispatch({
      type: ActionTypes.ADD_CONVERSATION,
      payload: conversation,
    });
  };

  // 대화 업데이트
  const updateConversation = (conversationId, updates) => {
    dispatch({
      type: ActionTypes.UPDATE_CONVERSATION,
      payload: { id: conversationId, updates },
    });
  };

  // 메시지 설정
  const setMessages = (messages) => {
    dispatch({
      type: ActionTypes.SET_MESSAGES,
      payload: messages,
    });
  };

  // 새 메시지 추가
  const addMessage = (message) => {
    const newMessage = {
      id: message.id || Date.now().toString(),
      role: message.role,
      content: message.content,
      tokenCount: message.tokenCount || 0,
      timestamp: message.timestamp || new Date().toISOString(),
    };

    dispatch({
      type: ActionTypes.ADD_MESSAGE,
      payload: newMessage,
    });

    // 현재 대화의 마지막 활동 시간 업데이트
    if (state.currentConversationId) {
      updateConversation(state.currentConversationId, {
        lastActivityAt: newMessage.timestamp,
      });
    }

    return newMessage;
  };

  // 메시지 업데이트 (스트리밍 중)
  const updateMessage = (messageId, updates) => {
    dispatch({
      type: ActionTypes.UPDATE_MESSAGE,
      payload: { id: messageId, updates },
    });
  };

  // 로딩 상태 설정
  const setLoading = (loading) => {
    dispatch({
      type: ActionTypes.SET_LOADING,
      payload: loading,
    });
  };

  // 에러 설정
  const setError = (error) => {
    dispatch({
      type: ActionTypes.SET_ERROR,
      payload: error,
    });
  };

  // 드로어 토글
  const toggleDrawer = (open) => {
    dispatch({
      type: ActionTypes.TOGGLE_DRAWER,
      payload: open,
    });
  };

  // 상태 초기화 (로그아웃시)
  const clearState = () => {
    dispatch({
      type: ActionTypes.CLEAR_STATE,
    });
  };

  // 현재 대화 정보 조회
  const getCurrentConversation = () => {
    return state.conversations.find(
      (conv) => conv.id === state.currentConversationId
    );
  };

  // 사용자 변경시 상태 초기화 및 대화 목록 로드
  useEffect(() => {
    if (user) {
      console.log("🔍 [DEBUG] ConversationContext - 사용자 로그인, 초기 대화 목록 로드");
      
      // 초기 대화 목록 로드
      const loadInitialConversations = async () => {
        try {
          console.log("🔍 [DEBUG] ConversationContext - 초기 대화 목록 로드 시작");
          const response = await conversationAPI.getConversations();
          console.log("🔍 [DEBUG] ConversationContext - 초기 대화 목록 로드 완료:", response.conversations?.length);
          setConversations(response.conversations || []);
        } catch (error) {
          console.error("ConversationContext - 초기 대화 목록 로드 실패:", error);
          // 실패해도 기본 빈 배열 유지
        }
      };
      
      loadInitialConversations();
    } else {
      clearState();
    }
  }, [user]);

  // Context value 최적화 - useMemo로 불필요한 재렌더링 방지
  const value = useMemo(() => ({
    // 상태
    ...state,

    // 액션 함수들
    setCurrentConversation,
    setConversations,
    addConversation,
    updateConversation,
    setMessages,
    addMessage,
    updateMessage,
    setLoading,
    setError,
    toggleDrawer,
    clearState,
    getCurrentConversation,
  }), [
    state,
    setCurrentConversation,
    setConversations,
    addConversation,
    updateConversation,
    setMessages,
    addMessage,
    updateMessage,
    setLoading,
    setError,
    toggleDrawer,
    clearState,
    getCurrentConversation,
  ]);

  return (
    <ConversationContext.Provider value={value}>
      {children}
    </ConversationContext.Provider>
  );
};

// Hook for using conversation context
export const useConversationContext = () => {
  const context = useContext(ConversationContext);
  if (!context) {
    throw new Error(
      "useConversationContext must be used within a ConversationProvider"
    );
  }
  return context;
};

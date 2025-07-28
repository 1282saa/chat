import React, { useState, useRef, useEffect, useCallback, memo } from "react";
import { useConversations } from "../../hooks/useConversations";
import { useConversationContext } from "../../contexts/ConversationContext";
import { conversationAPI } from "../../services/api";

const ConversationDrawer = memo(({
  isOpen,
  onClose,
  className = "",
  onCollapsedChange,
}) => {
  // ConversationContext에서 전역 대화 목록 사용
  const { 
    currentConversationId, 
    setCurrentConversation, 
    conversations: contextConversations 
  } = useConversationContext();
  
  // useConversations는 백업용으로만 사용
  const {
    conversations: hookConversations,
    loading,
    error,
    hasMore,
    loadMore,
    createConversation,
    deleteConversation,
    updateConversation,
  } = useConversations();

  // Context 대화가 없으면 hook 대화 사용 (초기 로드)
  const conversations = contextConversations?.length > 0 ? contextConversations : hookConversations;

  // 대화 목록 변경 감지 디버깅
  useEffect(() => {
    console.log("🎭 [DEBUG] ConversationDrawer - conversations 변경됨:", {
      contextCount: contextConversations?.length || 0,
      hookCount: hookConversations?.length || 0,
      finalCount: conversations.length,
      conversations: conversations.map(c => ({id: c.id, title: c.title}))
    });
  }, [contextConversations, hookConversations, conversations]);

  const [isCreating, setIsCreating] = useState(false);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [createError, setCreateError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [deleteError, setDeleteError] = useState(null);
  const [activeMenuId, setActiveMenuId] = useState(null);
  const [editingId, setEditingId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");

  // 대화 목록 스크롤을 위한 ref
  const conversationListRef = useRef(null);

  // 새 대화가 추가될 때마다 맨 아래로 스크롤
  useEffect(() => {
    if (
      conversationListRef.current &&
      conversations.length > 0 &&
      !isCollapsed
    ) {
      conversationListRef.current.scrollTop =
        conversationListRef.current.scrollHeight;
    }
  }, [conversations.length, isCollapsed]);

  // 외부 클릭 시 메뉴 닫기
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (activeMenuId && !event.target.closest(".conversation-menu")) {
        setActiveMenuId(null);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [activeMenuId]);

  // 새 대화 시작 (즉시 UI 전환) - 최적화된 버전
  const handleNewChat = useCallback(async () => {
    if (isCreating) return;

    // 🚀 즉시 UI 전환 (Optimistic Update)
    console.log("⚡ [FAST] 즉시 새 대화 모드로 전환");
    setCurrentConversation(null);
    
    // 모바일에서 사이드바 닫기
    if (window.innerWidth < 768) {
      onClose();
    }

    // 로딩 상태는 최소한으로만 표시
    setIsCreating(true);
    
    // 매우 짧은 시간 후 로딩 해제 (부드러운 전환)
    setTimeout(() => {
      setIsCreating(false);
      console.log("⚡ [FAST] 새 대화 준비 완료 - 사용자 입력 대기");
    }, 100);
  }, [setCurrentConversation, onClose]);

  // 대화 선택 - 최적화된 버전
  const handleSelectConversation = useCallback((conversationId) => {
    setCurrentConversation(conversationId);

    if (window.innerWidth < 768) {
      onClose();
    }
  }, [setCurrentConversation, onClose]);

  // 대화 삭제
  const handleDeleteConversation = async (conversationId, event) => {
    event.stopPropagation(); // 대화 선택을 방지

    if (!window.confirm("이 대화를 삭제하시겠습니까?")) {
      return;
    }

    setDeletingId(conversationId);
    setDeleteError(null);
    setActiveMenuId(null); // 메뉴 닫기

    try {
      await deleteConversation(conversationId);

      // 현재 선택된 대화가 삭제된 경우 첫 번째 대화로 이동
      if (
        currentConversationId === conversationId &&
        conversations.length > 1
      ) {
        const remainingConversations = conversations.filter(
          (conv) => conv.id !== conversationId
        );
        if (remainingConversations.length > 0) {
          setCurrentConversation(remainingConversations[0].id);
        }
      }

      console.log("대화 삭제 완료:", conversationId);
    } catch (error) {
      console.error("대화 삭제 중 오류:", error);
      // 일반적으로 API 오류가 발생해도 로컬에서는 삭제되므로 에러 표시하지 않음
      // setDeleteError('대화를 삭제할 수 없습니다. 다시 시도해주세요.');
      // setTimeout(() => setDeleteError(null), 3000);
    } finally {
      setDeletingId(null);
    }
  };

  // 대화 수정 시작
  const handleStartEdit = (conversationId, currentTitle, event) => {
    event.stopPropagation();
    setEditingId(conversationId);
    setEditingTitle(currentTitle);
    setActiveMenuId(null); // 메뉴 닫기
  };

  // 대화 수정 완료
  const handleSaveEdit = async (conversationId) => {
    if (!editingTitle.trim()) {
      setEditingId(null);
      setEditingTitle("");
      return;
    }

    try {
      // API 호출로 대화 제목 업데이트
      console.log("대화 제목 업데이트:", conversationId, editingTitle);
      await conversationAPI.updateConversation(conversationId, {
        title: editingTitle,
      });

      // 로컬 상태도 업데이트
      updateConversation(conversationId, { title: editingTitle });

      setEditingId(null);
      setEditingTitle("");

      console.log("대화 제목 수정 완료");
    } catch (error) {
      console.error("대화 제목 수정 중 오류:", error);
      // 사용자에게 에러 표시
      alert("제목 수정에 실패했습니다. 다시 시도해주세요.");
    }
  };

  // 대화 수정 취소
  const handleCancelEdit = () => {
    setEditingId(null);
    setEditingTitle("");
  };

  // 메뉴 토글
  const handleToggleMenu = (conversationId, event) => {
    event.stopPropagation();
    setActiveMenuId(activeMenuId === conversationId ? null : conversationId);
  };

  // 대화를 날짜별로 그룹화 - 메모이제이션 적용
  const groupConversationsByDate = useCallback((conversations) => {
    const groups = {};
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    conversations.forEach((conversation) => {
      const date = new Date(
        conversation.lastActivityAt || conversation.createdAt
      );
      const isToday = date.toDateString() === today.toDateString();
      const isYesterday = date.toDateString() === yesterday.toDateString();

      let key;
      if (isToday) {
        key = "Today";
      } else if (isYesterday) {
        key = "Yesterday";
      } else {
        const monthYear = date.toLocaleDateString("ko-KR", {
          year: "numeric",
          month: "2-digit",
        });
        key = monthYear;
      }

      if (!groups[key]) {
        groups[key] = [];
      }
      groups[key].push(conversation);
    });

    return groups;
  }, []);

  // 대화 그룹 최적화 - useMemo로 불필요한 재계산 방지
  const conversationGroups = React.useMemo(() => 
    groupConversationsByDate(conversations), 
    [conversations, groupConversationsByDate]
  );

  return (
    <>
      {/* 모바일 오버레이 */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-sm z-40 md:hidden transition-opacity duration-300"
          onClick={onClose}
        />
      )}

      {/* 드로어 컨테이너 */}
      <div
        className={`
        conversation-drawer
        fixed top-0 left-0 h-full z-[9999]
        bg-[#0d1117]
        border-r border-[#21262d] shadow-[inset_0_0_16px_rgba(0,0,0,0.4)]
        transform transition-all duration-300 ease-out will-change-transform
        ${isOpen ? "translate-x-0" : "-translate-x-full"}
        md:translate-x-0
        ${isCollapsed ? "w-14" : "w-full md:w-64"}
        ${className}
      `}
        style={{ overscrollBehavior: "contain" }}
      >
        {/* 헤더 - 접힌 상태에서는 숨김 */}
        {!isCollapsed && (
          <div className="flex items-center justify-between p-5 border-b border-[#21262d] relative transition-opacity duration-200 ease-in-out will-change-transform">
            <h1 className="text-xl font-semibold tracking-tight text-[#e6edf3]">
              TITLE-NOMICS
            </h1>

            {/* 미니멀 토글 버튼 */}
            <button
              onClick={() => {
                const newCollapsed = !isCollapsed;
                setIsCollapsed(newCollapsed);
                if (onCollapsedChange) {
                  onCollapsedChange(newCollapsed);
                }
              }}
              className="w-10 h-10 py-2 rounded-full bg-transparent hover:bg-[#11161f] transition-colors duration-200 flex items-center justify-center group"
              title="사이드바 접기"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="w-6 h-6 text-[#88929d] group-hover:text-[#e6edf3] transition-colors duration-200"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M18.75 19.5l-7.5-7.5 7.5-7.5m-6 15L5.25 12l7.5-7.5"
                />
              </svg>
            </button>
          </div>
        )}

        {/* 접힌 상태 전용 토글 버튼 */}
        {isCollapsed && (
          <div className="p-2 flex justify-center border-b border-[#21262d]">
            <button
              onClick={() => {
                const newCollapsed = !isCollapsed;
                setIsCollapsed(newCollapsed);
                if (onCollapsedChange) {
                  onCollapsedChange(newCollapsed);
                }
              }}
              className="w-10 h-10 py-2 rounded-full bg-transparent hover:bg-[#11161f] transition-colors duration-200 flex items-center justify-center group"
              title="사이드바 펼치기"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="w-6 h-6 text-[#88929d] group-hover:text-[#e6edf3] transition-colors duration-200 rotate-180"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M18.75 19.5l-7.5-7.5 7.5-7.5m-6 15L5.25 12l7.5-7.5"
                />
              </svg>
            </button>
          </div>
        )}

        {/* 새 대화 버튼 */}
        {!isCollapsed && (
          <div className="p-4 border-b border-[#21262d] transition-opacity duration-200 ease-in-out will-change-transform">
            <button
              onClick={handleNewChat}
              disabled={isCreating}
              className="group w-full flex items-center justify-start gap-3 px-3 py-2.5 text-[#e6edf3] hover:bg-[#21262d] disabled:bg-[#374151] rounded-lg text-sm transition-all duration-200 focus:outline-none border border-[#6e7681] hover:border-[#8b949e]"
              title="새 채팅"
            >
              {isCreating ? (
                <>
                  <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-[#e6edf3]"></div>
                  </div>
                  <span className="font-medium">생성 중...</span>
                </>
              ) : (
                <>
                  <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth="2"
                      stroke="currentColor"
                      className="h-4 w-4 group-hover:scale-110 transition-transform duration-200"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M12 4.5v15m7.5-7.5h-15"
                      />
                    </svg>
                  </div>
                  <span className="font-medium">새 채팅</span>
                </>
              )}
            </button>

            {(createError || deleteError) && (
              <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded text-center">
                <p className="text-xs text-red-400">
                  {createError || deleteError}
                </p>
              </div>
            )}
          </div>
        )}

        {/* 대화 목록 */}
        <div
          ref={conversationListRef}
          className="flex flex-col gap-0.5 overflow-y-auto h-[calc(100vh-210px)] custom-scrollbar"
          onScroll={(e) => e.stopPropagation()}
        >
          <style jsx>{`
            /* CSS Custom Properties for Design System */
            .conversation-drawer {
              --color-bg-primary: #0d1117;
              --color-bg-secondary: #11161f;
              --color-bg-tertiary: #161b22;
              --color-border: #21262d;
              --color-text-primary: #e6edf3;
              --color-text-secondary: #88929d;
              --color-accent: #10b981;
              --color-accent-hover: #059669;
              --color-danger: #f85149;
              --shadow-depth: inset 0 0 16px rgba(0, 0, 0, 0.4);
            }

            .custom-scrollbar::-webkit-scrollbar {
              width: 8px;
            }
            .custom-scrollbar::-webkit-scrollbar-track {
              background: transparent;
              border-radius: 4px;
            }
            .custom-scrollbar::-webkit-scrollbar-thumb {
              background: var(--color-border);
              border-radius: 4px;
              border: 1px solid var(--color-bg-primary);
            }
            .custom-scrollbar::-webkit-scrollbar-thumb:hover {
              background: #30363d;
            }
            .custom-scrollbar::-webkit-scrollbar-thumb:active {
              background: #484f58;
            }
            .custom-scrollbar::-webkit-scrollbar-corner {
              background: transparent;
            }

            /* 사이드바 스크롤 격리 */
            .custom-scrollbar {
              overscroll-behavior: contain;
              scroll-behavior: smooth;
            }
          `}</style>

          {error && !isCollapsed && (
            <div className="p-4 text-center bg-red-900/30 rounded-lg border border-red-700/50 mb-4">
              <div className="text-red-300 text-sm font-medium">{error}</div>
            </div>
          )}

          {conversations.length === 0 && !loading && !error && !isCollapsed && (
            <div className="p-6 text-center">
              <div className="w-12 h-12 mx-auto mb-4 bg-gradient-to-br from-gray-800/50 to-gray-900/50 rounded-2xl flex items-center justify-center shadow-lg border border-gray-700/30">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="1.5"
                  stroke="currentColor"
                  className="h-6 w-6 text-gray-400"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 0 1-.825-.242m9.345-8.334a2.126 2.126 0 0 0-.476-.095 48.64 48.64 0 0 0-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0 0 11.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155"
                  />
                </svg>
              </div>
              <h3 className="text-sm font-medium text-white mb-2 drop-shadow">
                아직 대화가 없습니다
              </h3>
              <p className="text-xs text-gray-400 leading-snug opacity-80">
                새 대화를 시작해서 AI와 대화해보세요!
              </p>
            </div>
          )}

          {/* 로딩 상태 */}
          {loading && conversations.length === 0 && !isCollapsed && (
            <div className="flex flex-col gap-1">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className="w-full h-10 px-3 bg-gray-900/40 animate-pulse flex items-center"
                >
                  <div className="h-3 bg-gray-700/40 rounded w-3/4"></div>
                </div>
              ))}
            </div>
          )}

          {/* 딥시크 스타일 대화 목록 */}
          {!isCollapsed && conversations.length > 0 && (
            <div className="flex flex-col gap-1 transition-opacity duration-200 ease-in-out will-change-transform">
              {Object.entries(conversationGroups).map(
                ([groupTitle, groupConversations]) => (
                  <div key={groupTitle}>
                    {/* 날짜 그룹 헤더 */}
                    <div className="text-xs text-white/40 uppercase tracking-wide py-2 px-3 font-medium">
                      {groupTitle}
                    </div>

                    {/* 그룹 내 대화들 */}
                    {groupConversations.map((conversation) => (
                      <div
                        key={conversation.id}
                        className={`
                        flex items-center justify-between h-10 px-3 py-2 text-sm transition-colors duration-200 relative
                        ${
                          currentConversationId === conversation.id
                            ? "bg-[#161b22] text-[#e6edf3] relative before:absolute before:left-0 before:top-0 before:bottom-0 before:w-[2px] before:bg-[#10b981]"
                            : "text-[#88929d] hover:bg-[#11161f] hover:text-[#e6edf3]"
                        }
                      `}
                      >
                        {editingId === conversation.id ? (
                          // 수정 모드
                          <div className="flex-1 flex items-center gap-2">
                            <input
                              type="text"
                              value={editingTitle}
                              onChange={(e) => setEditingTitle(e.target.value)}
                              onKeyPress={(e) => {
                                if (e.key === "Enter") {
                                  handleSaveEdit(conversation.id);
                                } else if (e.key === "Escape") {
                                  handleCancelEdit();
                                }
                              }}
                              className="flex-1 bg-[#0d1117] border border-[#21262d] rounded px-2 py-1 text-sm text-[#e6edf3] focus:outline-none focus:border-[#10b981]"
                              autoFocus
                            />
                            <button
                              onClick={() => handleSaveEdit(conversation.id)}
                              className="p-1 text-[#10b981] hover:bg-[#161b22] rounded"
                              title="저장"
                            >
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth="2"
                                stroke="currentColor"
                                className="h-4 w-4"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="m4.5 12.75 6 6 9-13.5"
                                />
                              </svg>
                            </button>
                            <button
                              onClick={handleCancelEdit}
                              className="p-1 text-[#88929d] hover:text-[#f85149] hover:bg-[#161b22] rounded"
                              title="취소"
                            >
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                fill="none"
                                viewBox="0 0 24 24"
                                strokeWidth="2"
                                stroke="currentColor"
                                className="h-4 w-4"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  d="M6 18L18 6M6 6l12 12"
                                />
                              </svg>
                            </button>
                          </div>
                        ) : (
                          // 일반 모드
                          <>
                            <button
                              onClick={() =>
                                handleSelectConversation(conversation.id)
                              }
                              className="flex-1 text-left truncate focus:outline-none py-2"
                              title={conversation.title}
                            >
                              <span className="truncate text-sm font-medium">
                                {conversation.title || "새 대화"}
                              </span>
                            </button>

                            {/* 메뉴 버튼 */}
                            <div className="conversation-menu relative">
                              <button
                                onClick={(e) =>
                                  handleToggleMenu(conversation.id, e)
                                }
                                className="ml-2 py-2 px-2 text-[#88929d] hover:text-[#e6edf3] transition-colors duration-200 flex-shrink-0 rounded-md hover:bg-[#161b22]"
                                title="메뉴"
                              >
                                <svg
                                  xmlns="http://www.w3.org/2000/svg"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  strokeWidth="1.5"
                                  stroke="currentColor"
                                  className="h-5 w-5"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    d="M6.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM12.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM18.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z"
                                  />
                                </svg>
                              </button>

                              {/* 드롭다운 메뉴 */}
                              {activeMenuId === conversation.id && (
                                <div className="absolute right-0 top-full mt-1 bg-[#21262d] border border-[#30363d] rounded-md shadow-lg z-50 min-w-[120px]">
                                  <button
                                    onClick={(e) =>
                                      handleStartEdit(
                                        conversation.id,
                                        conversation.title,
                                        e
                                      )
                                    }
                                    className="w-full px-3 py-2 text-sm text-[#e6edf3] hover:bg-[#30363d] flex items-center gap-2 transition-colors duration-200"
                                  >
                                    <svg
                                      xmlns="http://www.w3.org/2000/svg"
                                      fill="none"
                                      viewBox="0 0 24 24"
                                      strokeWidth="1.5"
                                      stroke="currentColor"
                                      className="h-4 w-4"
                                    >
                                      <path
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10"
                                      />
                                    </svg>
                                    수정
                                  </button>
                                  <button
                                    onClick={(e) =>
                                      handleDeleteConversation(
                                        conversation.id,
                                        e
                                      )
                                    }
                                    disabled={deletingId === conversation.id}
                                    className="w-full px-3 py-2 text-sm text-[#f85149] hover:bg-[#30363d] flex items-center gap-2 transition-colors duration-200 disabled:opacity-50"
                                  >
                                    {deletingId === conversation.id ? (
                                      <div className="animate-spin rounded-full h-4 w-4 border-b border-[#f85149]"></div>
                                    ) : (
                                      <svg
                                        xmlns="http://www.w3.org/2000/svg"
                                        fill="none"
                                        viewBox="0 0 24 24"
                                        strokeWidth="1.5"
                                        stroke="currentColor"
                                        className="h-4 w-4"
                                      >
                                        <path
                                          strokeLinecap="round"
                                          strokeLinejoin="round"
                                          d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
                                        />
                                      </svg>
                                    )}
                                    삭제
                                  </button>
                                </div>
                              )}
                            </div>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                )
              )}
            </div>
          )}

          {/* 접힌 상태 새 대화 버튼만 표시 */}
          {isCollapsed && (
            <div className="flex flex-col items-center p-2 transition-opacity duration-200 ease-in-out will-change-transform">
              <button
                onClick={handleNewChat}
                disabled={isCreating}
                className="w-10 h-10 bg-[#21262d] hover:bg-[#30363d] disabled:bg-[#374151] text-white rounded-full flex items-center justify-center transition-colors duration-200 focus:outline-none border border-[#30363d] hover:border-[#444c56]"
                title="새 대화"
              >
                {isCreating ? (
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                ) : (
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth="2"
                    stroke="currentColor"
                    className="h-6 w-6"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 4.5v15m7.5-7.5h-15"
                    />
                  </svg>
                )}
              </button>
            </div>
          )}
        </div>

        {/* 추가 로딩 인디케이터 - 더 많은 대화 로드 시 */}
        {loading && conversations.length > 0 && (
          <div className="p-4 text-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-300 mx-auto"></div>
          </div>
        )}

        {/* 더 보기 버튼 */}
        {hasMore && !loading && conversations.length > 0 && !isCollapsed && (
          <div className="p-4 text-center">
            <button
              onClick={loadMore}
              className="text-xs text-white/60 hover:text-white/80 transition-colors duration-200 px-3 py-1.5 hover:bg-gray-800/40 rounded"
            >
              더 보기
            </button>
          </div>
        )}
      </div>
    </>
  );
});

export default ConversationDrawer;

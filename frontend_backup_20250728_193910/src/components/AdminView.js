import React, { useState, useEffect } from "react";
import ChatWindow from "./chat/ChatWindow";
import PromptCardManager from "./PromptCardManager";
import ConversationDrawer from "./chat/ConversationDrawer";
import { promptCardAPI } from "../services/api";
import { ChatInterfaceSkeleton } from "./skeleton/SkeletonComponents";

const AdminView = ({ projectId, projectName }) => {
  const [promptCards, setPromptCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rightSidebarCollapsed, setRightSidebarCollapsed] = useState(false);

  useEffect(() => {
    const loadPromptCards = async () => {
      try {
        setLoading(true);
        const response = await promptCardAPI.getPromptCards(projectId, true);
        setPromptCards(response.promptCards || []);
      } catch (error) {
        console.warn("프롬프트 카드 로드 실패:", error);
        setPromptCards([]);
      } finally {
        setLoading(false);
      }
    };

    loadPromptCards();
  }, [projectId]);

  if (loading) {
    return <ChatInterfaceSkeleton />;
  }

  return (
    <div className="flex h-screen bg-white dark:bg-dark-primary transition-colors duration-300">
      {/* 좌측 대화 쓰레드 사이드바 */}
      <ConversationDrawer onCollapsedChange={setSidebarCollapsed} />

      {/* 중앙 채팅 영역 */}
      <div className={`flex-1 transition-all duration-500 ease-out ${
        sidebarCollapsed ? "md:ml-14" : "md:ml-64"
      } ${
        rightSidebarCollapsed ? "md:mr-0" : "md:mr-80"
      }`}>
        <ChatWindow
          projectId={projectId}
          projectName={projectName}
          promptCards={promptCards}
          isAdminMode={true}
        />
      </div>

      {/* 우측 프롬프트 카드 사이드바 */}
      <div className={`fixed right-0 top-0 h-full bg-white dark:bg-dark-secondary border-l border-gray-200 dark:border-gray-700 transition-all duration-500 ease-out z-30 ${
        rightSidebarCollapsed ? "w-0 overflow-hidden" : "w-80"
      }`}>
        <div className="h-full flex flex-col">
          {/* 헤더 */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">
              프롬프트 관리
            </h3>
            <button
              onClick={() => setRightSidebarCollapsed(!rightSidebarCollapsed)}
              className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          
          {/* 프롬프트 카드 매니저 */}
          <div className="flex-1 overflow-hidden">
            <PromptCardManager projectId={projectId} projectName={projectName} />
          </div>
        </div>
      </div>

      {/* 우측 사이드바 토글 버튼 (사이드바가 닫혀있을 때만 표시) */}
      {rightSidebarCollapsed && (
        <button
          onClick={() => setRightSidebarCollapsed(false)}
          className="fixed right-4 top-4 z-40 p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-lg transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>
      )}
    </div>
  );
};

export default AdminView;

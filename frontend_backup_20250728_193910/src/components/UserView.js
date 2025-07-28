import React, { useState, useEffect } from "react";
import { promptCardAPI } from "../services/api";
import ChatWindow from "./chat/ChatWindow";
import { ChatInterfaceSkeleton } from "./skeleton/SkeletonComponents";

const UserView = ({ projectId, projectName }) => {
  const [promptCards, setPromptCards] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadPromptCards = async () => {
      try {
        setLoading(true);
        // AdminView와 동일하게 includeContent=true로 설정하여 프롬프트 내용을 포함하여 로드
        const response = await promptCardAPI.getPromptCards(projectId, true);
        // 응답 구조가 AdminView와 동일하게 처리
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
    <div className="h-screen bg-white dark:bg-dark-primary transition-colors duration-300">
      <ChatWindow
        projectId={projectId}
        projectName={projectName}
        promptCards={promptCards}
      />
    </div>
  );
};

export default UserView;

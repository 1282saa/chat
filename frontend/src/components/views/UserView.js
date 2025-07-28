import React, { useState, useEffect } from "react";
import { promptCardAPI } from "../../services/api";
import ChatWindow from "../news/chat/ChatWindow";
import { ChatInterfaceSkeleton } from "../ui/skeleton/SkeletonComponents";

const UserView = () => {
  const [promptCards, setPromptCards] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadPromptCards = async () => {
      try {
        setLoading(true);
        // 사용자별 프롬프트 카드 로드
        const response = await promptCardAPI.getPromptCards(null, true);
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
  }, []);

  if (loading) {
    return <ChatInterfaceSkeleton />;
  }

  return (
    <div className="h-screen bg-white dark:bg-dark-primary transition-colors duration-300">
      <ChatWindow promptCards={promptCards} />
    </div>
  );
};

export default UserView;

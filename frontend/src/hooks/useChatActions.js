import { useState, useCallback } from "react";
import { toast } from "react-hot-toast";

/**
 * 채팅 액션 관리를 위한 커스텀 훅
 * 복사, 리셋 등의 사용자 액션 처리
 */
export const useChatActions = () => {
  const [copiedMessage, setCopiedMessage] = useState(null);

  // 메시지 복사
  const handleCopyMessage = useCallback(async (content, messageId) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedMessage(messageId);
      toast.success("메시지가 복사되었습니다!");

      // 3초 후 복사 상태 초기화
      setTimeout(() => {
        setCopiedMessage(null);
      }, 3000);
    } catch (error) {
      console.error("복사 실패:", error);
      toast.error("복사에 실패했습니다.");
    }
  }, []);

  // 제목 복사
  const handleCopyTitle = useCallback(async (title, messageId, index) => {
    try {
      await navigator.clipboard.writeText(title);
      setCopiedMessage(`${messageId}-title-${index}`);
      toast.success("제목이 복사되었습니다!");

      // 3초 후 복사 상태 초기화
      setTimeout(() => {
        setCopiedMessage(null);
      }, 3000);
    } catch (error) {
      console.error("제목 복사 실패:", error);
      toast.error("복사에 실패했습니다.");
    }
  }, []);

  // 채팅 초기화
  const resetChat = useCallback((setMessages, clearInput) => {
    console.log("채팅 초기화");
    setMessages([]);
    if (clearInput) clearInput();
    toast.success("채팅이 초기화되었습니다.");
  }, []);

  return {
    copiedMessage,
    handleCopyMessage,
    handleCopyTitle,
    resetChat,
  };
};

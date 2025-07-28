import { useState, useRef, useCallback } from "react";

/**
 * 채팅 스크롤 관리를 위한 커스텀 훅
 * 자동 스크롤, 사용자 스크롤 감지, 스크롤 위치 관리
 */
export const useChatScroll = () => {
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const scrollContainerRef = useRef(null);
  const lastScrollTopRef = useRef(0);
  const messagesEndRef = useRef(null);

  // 사용자 스크롤 감지
  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current) return;

    const container = scrollContainerRef.current;
    const currentScrollTop = container.scrollTop;
    const maxScrollTop = container.scrollHeight - container.clientHeight;

    // 사용자가 수동으로 스크롤했는지 감지
    if (Math.abs(currentScrollTop - lastScrollTopRef.current) > 2) {
      const isAtBottom = currentScrollTop >= maxScrollTop - 20;

      // 하단에 있을 때만 자동 스크롤 허용, 그 외는 사용자 스크롤 모드
      setIsUserScrolling(!isAtBottom);
    }

    lastScrollTopRef.current = currentScrollTop;
  }, []);

  // 하단으로 스크롤
  const scrollToBottom = useCallback(() => {
    if (messagesEndRef.current && !isUserScrolling) {
      messagesEndRef.current.scrollIntoView({
        behavior: "smooth",
        block: "end",
      });

      // 스크롤 위치 업데이트
      setTimeout(() => {
        if (scrollContainerRef.current) {
          lastScrollTopRef.current =
            scrollContainerRef.current.scrollHeight -
            scrollContainerRef.current.clientHeight;
        }
      }, 100);
    }
  }, [isUserScrolling]);

  // 강제 스크롤 (사용자 스크롤 무시)
  const forceScrollToBottom = useCallback(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({
        behavior: "smooth",
        block: "end",
      });
      setIsUserScrolling(false);
    }
  }, []);

  return {
    isUserScrolling,
    scrollContainerRef,
    messagesEndRef,
    handleScroll,
    scrollToBottom,
    forceScrollToBottom,
  };
};

import React, { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";

/**
 * 실시간 타이핑 효과 컴포넌트
 * WebSocket으로 받은 텍스트 청크를 실시간으로 타이핑하듯 표시
 */
const RealTimeTyping = ({
  content = "",
  isStreaming = false,
  typingSpeed = 30, // ms per character
  className = "",
  enableMarkdown = true,
}) => {
  const [displayedContent, setDisplayedContent] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isTyping, setIsTyping] = useState(false);
  const typingTimerRef = useRef(null);
  const previousContentRef = useRef("");

  // 새로운 컨텐츠가 들어왔을 때 타이핑 효과 시작
  useEffect(() => {
    const newContent = content || "";
    const previousContent = previousContentRef.current;

    // 컨텐츠가 변경되었을 때만 처리
    if (newContent !== previousContent) {
      console.log("🎬 실시간 타이핑 업데이트:", {
        previousLength: previousContent.length,
        newLength: newContent.length,
        isStreaming,
        newText: newContent.slice(previousContent.length),
      });

      // 이전에 표시된 텍스트는 유지하고, 새로운 부분만 타이핑
      if (newContent.startsWith(previousContent)) {
        // 새로운 텍스트가 기존 텍스트의 확장인 경우
        setCurrentIndex(previousContent.length);
        setIsTyping(true);
      } else {
        // 완전히 새로운 텍스트인 경우 처음부터 시작
        setDisplayedContent("");
        setCurrentIndex(0);
        setIsTyping(true);
      }

      previousContentRef.current = newContent;
    }
  }, [content, isStreaming]);

  // 타이핑 애니메이션 효과
  useEffect(() => {
    if (!isTyping) return;

    const targetContent = content || "";

    if (currentIndex < targetContent.length) {
      // 문자별로 다른 타이핑 속도 적용 (더 자연스럽게)
      const nextChar = targetContent[currentIndex];
      let charTypingSpeed = typingSpeed;

      // 공백이나 구두점에서는 약간 더 빠르게
      if (/[\s.,!?;:]/.test(nextChar)) {
        charTypingSpeed = typingSpeed * 0.7;
      }
      // 줄바꿈에서는 더 빠르게
      else if (nextChar === "\n") {
        charTypingSpeed = typingSpeed * 0.3;
      }

      typingTimerRef.current = setTimeout(() => {
        setDisplayedContent((prev) => prev + nextChar);
        setCurrentIndex((prev) => prev + 1);
      }, charTypingSpeed);
    } else {
      // 타이핑 완료
      setIsTyping(false);

      // 스트리밍이 완료되지 않았다면 계속 대기
      if (isStreaming) {
        console.log("✅ 현재 청크 타이핑 완료, 다음 청크 대기 중...");
      } else {
        console.log("🎉 전체 타이핑 완료!");
      }
    }

    return () => {
      if (typingTimerRef.current) {
        clearTimeout(typingTimerRef.current);
      }
    };
  }, [currentIndex, content, isTyping, typingSpeed, isStreaming]);

  // 컴포넌트 언마운트 시 타이머 정리
  useEffect(() => {
    return () => {
      if (typingTimerRef.current) {
        clearTimeout(typingTimerRef.current);
      }
    };
  }, []);

  // 실시간 타이핑 커서 표시 여부
  const showCursor = isStreaming || isTyping;

  // 표시할 컨텐츠 결정
  const contentToShow = displayedContent;

  return (
    <div className={`relative ${className}`}>
      {enableMarkdown ? (
        <div className="text-[15px] font-normal leading-[1.6] whitespace-pre-wrap [&>p]:mb-3 [&>ul]:mb-3 [&>ol]:mb-3 [&>h1]:text-[18px] [&>h1]:font-semibold [&>h1]:mb-3 [&>h2]:text-[16px] [&>h2]:font-semibold [&>h2]:mb-2 [&>h3]:text-[15px] [&>h3]:font-medium [&>h3]:mb-2">
          <ReactMarkdown>{contentToShow}</ReactMarkdown>
          {showCursor && (
            <span className="inline-block w-0.5 h-5 bg-blue-500 animate-pulse ml-1 align-middle" />
          )}
        </div>
      ) : (
        <div className="text-[15px] font-normal leading-[1.6] whitespace-pre-wrap">
          {contentToShow}
          {showCursor && (
            <span className="inline-block w-0.5 h-5 bg-blue-500 animate-pulse ml-1 align-middle" />
          )}
        </div>
      )}
    </div>
  );
};

export default RealTimeTyping;

import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";

/**
 * 타이핑 애니메이션 텍스트 컴포넌트
 */
const TypingText = ({
  text = "",
  isTyping = false,
  speed = 20,
  className = "",
  onComplete = null,
}) => {
  const [displayedText, setDisplayedText] = useState("");
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    // 타이핑 애니메이션이 비활성화되면 전체 텍스트 표시
    if (!isTyping || !text) {
      setDisplayedText(text);
      return;
    }

    // 타이핑 애니메이션 시작
    setDisplayedText("");
    setCurrentIndex(0);

    const timer = setInterval(() => {
      setCurrentIndex((prevIndex) => {
        const nextIndex = prevIndex + 1;

        if (nextIndex <= text.length) {
          setDisplayedText(text.slice(0, nextIndex));

          // 타이핑 완료 시
          if (nextIndex === text.length) {
            clearInterval(timer);
            if (onComplete) onComplete();
          }

          return nextIndex;
        } else {
          clearInterval(timer);
          return prevIndex;
        }
      });
    }, speed);

    return () => clearInterval(timer);
  }, [text, isTyping, speed, onComplete]);

  return (
    <div className={className}>
      <ReactMarkdown>{displayedText}</ReactMarkdown>
      {isTyping && currentIndex < text.length && (
        <span className="animate-pulse">|</span>
      )}
    </div>
  );
};

export default TypingText;

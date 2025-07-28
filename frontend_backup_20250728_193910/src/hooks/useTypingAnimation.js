import { useState, useEffect, useRef } from "react";

/**
 * 타이핑 애니메이션을 위한 커스텀 훅
 * @param {string} text - 표시할 전체 텍스트
 * @param {boolean} isTyping - 타이핑 애니메이션 활성화 여부
 * @param {number} speed - 타이핑 속도 (밀리초)
 * @param {boolean} isComplete - 메시지 완료 여부
 */
export const useTypingAnimation = (
  text,
  isTyping = false,
  speed = 30,
  isComplete = false
) => {
  const [displayedText, setDisplayedText] = useState("");
  const [isAnimating, setIsAnimating] = useState(false);
  const intervalRef = useRef(null);
  const indexRef = useRef(0);

  useEffect(() => {
    // 타이핑 애니메이션이 비활성화되거나 텍스트가 없으면 전체 텍스트 반환
    if (!isTyping || !text || !isComplete) {
      setDisplayedText(text || "");
      setIsAnimating(false);
      return;
    }

    // 이미 애니메이션 중이면 중단하고 새로 시작
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }

    // 초기화
    setDisplayedText("");
    setIsAnimating(true);
    indexRef.current = 0;

    // 타이핑 애니메이션 시작
    intervalRef.current = setInterval(() => {
      const currentIndex = indexRef.current;

      if (currentIndex < text.length) {
        setDisplayedText(text.slice(0, currentIndex + 1));
        indexRef.current = currentIndex + 1;
      } else {
        // 애니메이션 완료
        clearInterval(intervalRef.current);
        setIsAnimating(false);
        setDisplayedText(text);
      }
    }, speed);

    // 클린업 함수
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [text, isTyping, speed, isComplete]);

  // 컴포넌트 언마운트 시 클린업
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    displayedText,
    isAnimating,
    // 애니메이션 완전히 스킵하는 함수
    skipAnimation: () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      setDisplayedText(text);
      setIsAnimating(false);
    },
  };
};

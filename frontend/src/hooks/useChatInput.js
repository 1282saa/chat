import { useState, useRef, useCallback } from "react";

/**
 * 채팅 입력 관리를 위한 커스텀 훅
 * 입력값, 높이 조절, 키보드 이벤트 관리
 */
export const useChatInput = () => {
  const [inputValue, setInputValue] = useState("");
  const [inputHeight, setInputHeight] = useState(24);
  const inputRef = useRef(null);

  // 입력창 높이 자동 조절
  const adjustInputHeight = useCallback((value) => {
    if (!inputRef.current) return;

    const lines = value.split("\n");
    const lineHeight = 24; // 기본 줄 높이
    const padding = 16; // 상하 패딩
    const maxHeight = lineHeight * 5 + padding; // 최대 5줄
    const minHeight = lineHeight + padding; // 최소 1줄

    let newHeight = lineHeight * Math.max(1, lines.length) + padding;
    newHeight = Math.min(newHeight, maxHeight);
    newHeight = Math.max(newHeight, minHeight);

    setInputHeight(newHeight);
  }, []);

  // 입력값 변경 처리
  const handleInputChange = useCallback(
    (e) => {
      const value = e.target.value;
      setInputValue(value);
      adjustInputHeight(value);
    },
    [adjustInputHeight]
  );

  // 키보드 이벤트 처리
  const handleKeyPress = useCallback(
    (e, onSend) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        if (inputValue.trim() && onSend) {
          onSend();
        }
      }
    },
    [inputValue]
  );

  // 입력값 초기화
  const clearInput = useCallback(() => {
    setInputValue("");
    setInputHeight(24);
  }, []);

  return {
    inputValue,
    inputHeight,
    inputRef,
    handleInputChange,
    handleKeyPress,
    clearInput,
  };
};

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { ExclamationTriangleIcon } from "@heroicons/react/24/outline";
import {
  parseCitations,
  renderSourcesList,
  preprocessMessageContent,
} from "../../utils/citationUtils";
import RealTimeTyping from "./RealTimeTyping";

// Enhanced Agent System 사고 과정 컴포넌트
const ThinkingProcess = ({ steps }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!steps || steps.length === 0) return null;

  return (
    <div className="mt-4 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-gray-50 dark:bg-gray-800/50">
      {/* 헤더 - 클릭 가능 */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-100 dark:hover:bg-gray-700/50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg
            className="w-5 h-5 text-purple-500"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.847a4.5 4.5 0 003.09 3.09L15.75 12l-2.847.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"
            />
          </svg>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            AI 사고 과정 ({steps.length}단계)
          </span>
        </div>
        <svg
          className={`w-4 h-4 text-gray-500 transition-transform ${
            isExpanded ? "rotate-180" : ""
          }`}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {/* 내용 - 접기/펼치기 */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-3">
          {steps.map((step, index) => (
            <div key={index} className="flex gap-3 py-2">
              {/* 단계 번호 */}
              <div className="flex-shrink-0 w-6 h-6 bg-purple-500 text-white text-xs font-medium rounded-full flex items-center justify-center">
                {index + 1}
              </div>

              {/* 단계 내용 */}
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-1">
                  {step.step_name || `단계 ${index + 1}`}
                </div>
                <div className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                  {step.description || step.result || "처리 중..."}
                </div>
                {step.execution_time && (
                  <div className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                    실행 시간: {step.execution_time.toFixed(1)}초
                  </div>
                )}
              </div>

              {/* 결과 상태 */}
              <div className="flex-shrink-0">
                {step.result === "성공" || step.result?.includes("성공") ? (
                  <svg
                    className="w-4 h-4 text-green-500"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                ) : step.result === "실패" || step.result?.includes("실패") ? (
                  <svg
                    className="w-4 h-4 text-red-500"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                ) : (
                  <svg
                    className="w-4 h-4 text-blue-500"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// 타임스탬프 포맷팅 유틸리티 함수
const formatTimestamp = (timestamp) => {
  if (!timestamp) return "";

  try {
    // 이미 Date 객체인 경우
    if (timestamp instanceof Date) {
      return timestamp.toLocaleTimeString("ko-KR", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    }

    // 문자열인 경우 Date 객체로 변환
    if (typeof timestamp === "string") {
      const date = new Date(timestamp);
      return isNaN(date.getTime())
        ? ""
        : date.toLocaleTimeString("ko-KR", {
            hour: "2-digit",
            minute: "2-digit",
            hour12: false,
          });
    }

    // 숫자인 경우 (타임스탬프)
    if (typeof timestamp === "number") {
      return new Date(timestamp).toLocaleTimeString("ko-KR", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
    }

    return "";
  } catch (error) {
    console.warn("타임스탬프 포맷 오류:", error);
    return "";
  }
};

const SimpleChatMessage = React.memo(
  ({ message, onCopyMessage, onCopyTitle, copiedMessage }) => {
    // 사용자가 대화창에서 전송한 메시지면 사용자 메시지!
    const isUser = message.role === "user" || message.type === "user";
    const isError = message.role === "error";
    const isLoading = message.isLoading || false;

    // 버튼 상태 관리
    const [likeClicked, setLikeClicked] = useState(false);
    const [dislikeClicked, setDislikeClicked] = useState(false);
    const [copyClicked, setCopyClicked] = useState(false);

    // 출처 정보 (Knowledge Base에서 온 경우)
    const sources = message.sources || [];

    console.log("📚 실제 sources 데이터:", sources);

    // 🔗 기사 미리보기 핸들러 (현재는 URL로 이동)
    const handlePreviewArticle = (article) => {
      console.log("🔍 기사 미리보기 요청:", article);

      // URL이 있으면 새 창에서 열기
      if (article?.url) {
        window.open(article.url, "_blank", "noopener,noreferrer");
      } else {
        // URL이 없으면 콘솔에 정보만 출력 (추후 모달 구현 가능)
        console.warn(
          "⚠️ 기사 URL이 없어 미리보기를 표시할 수 없습니다:",
          article
        );
      }
    };

    // 메시지 내용 처리 (각주 포함)
    const renderMessageContent = (content) => {
      if (!content) return null;

      // 디버깅: sources 정보 로깅
      console.log("📚 SimpleChatMessage - sources:", sources);
      console.log(
        "📝 SimpleChatMessage - content 일부:",
        content.substring(0, 200)
      );

      // 각주 패턴이 있는지 확인 ([1], [2] 등)
      const hasCitations = /\[\d+\]/g.test(content);
      console.log("🔍 각주 패턴 발견:", hasCitations);

      // 각주가 있는 경우 파싱하여 각주 링크로 변환
      if (hasCitations) {
        const processedContent = preprocessMessageContent(content);
        const parsedContent = parseCitations(
          processedContent,
          sources,
          handlePreviewArticle
        );

        console.log("🔗 파싱된 각주 컨텐츠:", parsedContent);

        return (
          <div className="text-[15px] font-normal leading-[1.6] whitespace-pre-wrap [&>p]:mb-3 [&>ul]:mb-3 [&>ol]:mb-3 [&>h1]:text-[18px] [&>h1]:font-semibold [&>h1]:mb-3 [&>h2]:text-[16px] [&>h2]:font-semibold [&>h2]:mb-2 [&>h3]:text-[15px] [&>h3]:font-medium [&>h3]:mb-2">
            {parsedContent.map((part, index) => (
              <span key={index}>{part}</span>
            ))}
          </div>
        );
      }

      // 일반 마크다운 렌더링
      return (
        <div className="text-[15px] font-normal leading-[1.6] whitespace-pre-wrap [&>p]:mb-3 [&>ul]:mb-3 [&>ol]:mb-3 [&>h1]:text-[18px] [&>h1]:font-semibold [&>h1]:mb-3 [&>h2]:text-[16px] [&>h2]:font-semibold [&>h2]:mb-2 [&>h3]:text-[15px] [&>h3]:font-medium [&>h3]:mb-2">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      );
    };

    return (
      <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
        {isUser ? (
          // 사용자 메시지 - 우측 말풍선
          <div className="max-w-[70%]">
            <div className="bg-[#5E89FF] text-white rounded-2xl px-4 py-2 shadow-md">
              <div className="text-[15px] font-normal leading-[1.5] whitespace-pre-wrap break-words">
                {message.content}
              </div>
              {/* 타임스탬프 - 말풍선 내부 하단 */}
              {message.timestamp && (
                <div className="text-[12px] text-white/70 mt-1 text-right">
                  {formatTimestamp(message.timestamp)}
                </div>
              )}
            </div>
          </div>
        ) : (
          // AI 메시지 - 좌측 플랫형 답변
          <div className="w-full max-w-[75%]">
            <div
              className="bg-transparent dark:bg-transparent"
              aria-live="polite"
            >
              {isError ? (
                <div className="text-red-600 dark:text-red-400">
                  <div className="flex items-center mb-2">
                    <ExclamationTriangleIcon className="h-4 w-4 mr-2" />
                    <span className="text-[14px] font-semibold">
                      오류가 발생했습니다
                    </span>
                  </div>
                  <div className="text-[15px] font-normal leading-[1.5]">
                    {message.content}
                  </div>
                </div>
              ) : isLoading ? (
                // 스트리밍 중 - 실시간 텍스트 표시
                <div className="flex items-start gap-3">
                  {/* AI 아이콘 */}
                  <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-indigo-400 to-purple-500 rounded-full flex items-center justify-center shadow-sm mt-1">
                    <svg
                      className="w-4 h-4 text-white"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.847a4.5 4.5 0 003.09 3.09L15.75 12l-2.847.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"
                      />
                    </svg>
                  </div>

                  {/* 실시간 스트리밍 텍스트 */}
                  <div className="flex-1 text-[#202124] dark:text-[#E5E7EB] prose prose-sm max-w-none">
                    <RealTimeTyping 
                      content={message.content}
                      isStreaming={message.isStreaming}
                      typingSpeed={15}
                      enableMarkdown={true}
                      className="text-[#202124] dark:text-[#E5E7EB]"
                    />
                  </div>
                </div>
              ) : (
                // 일반 AI 응답 - 제미나이 스타일 로고 포함
                <div className="flex items-start gap-3">
                  {/* AI 아이콘 */}
                  <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-indigo-400 to-purple-500 rounded-full flex items-center justify-center shadow-sm mt-1">
                    <svg
                      className="w-4 h-4 text-white"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.847a4.5 4.5 0 003.09 3.09L15.75 12l-2.847.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456z"
                      />
                    </svg>
                  </div>

                  {/* 답변 내용 */}
                  <div className="flex-1 text-[#202124] dark:text-[#E5E7EB] prose prose-sm max-w-none">
                    <div className="inline">
                      {renderMessageContent(message.content)}
                    </div>

                    {/* 출처 목록 (Knowledge Base 검색 결과인 경우) */}
                    {sources.length > 0 && renderSourcesList(sources)}

                    {/* Enhanced Agent System 사고 과정 (있는 경우) */}
                    {message.thinkingProcess &&
                      message.thinkingProcess.length > 0 && (
                        <ThinkingProcess steps={message.thinkingProcess} />
                      )}
                  </div>
                </div>
              )}
              {/* 타임스탬프 - 아이콘 위치에 맞춘 여백 */}
              {message.timestamp && (
                <div className="text-[12px] text-gray-500 dark:text-gray-400 mt-1 ml-11">
                  {formatTimestamp(message.timestamp)}
                </div>
              )}
            </div>

            {/* AI 메시지 하단 액션 버튼들 - GPT 스타일 */}
            {!isError && !isLoading && (
              <div className="flex items-center gap-1 mt-2 ml-11">
                {/* 복사 버튼 */}
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(message.content);
                    setCopyClicked(true);
                    setTimeout(() => setCopyClicked(false), 1000);
                  }}
                  className={`p-1.5 rounded transition-all duration-200 transform ${
                    copyClicked
                      ? "text-green-500 bg-green-100 dark:bg-green-900/30 scale-110"
                      : "text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                  }`}
                  title={copyClicked ? "복사됨!" : "복사"}
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    {copyClicked ? (
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M5 13l4 4L19 7"
                      />
                    ) : (
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
                    )}
                  </svg>
                </button>

                {/* 좋아요 버튼 */}
                <button
                  onClick={() => {
                    setLikeClicked(true);
                    setDislikeClicked(false);
                    setTimeout(() => setLikeClicked(false), 2000);
                  }}
                  className={`p-1.5 rounded transition-all duration-300 transform ${
                    likeClicked
                      ? "text-blue-500 bg-blue-100 dark:bg-blue-900/30 scale-110 animate-pulse"
                      : "text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                  }`}
                  title={likeClicked ? "좋아요!" : "좋아요"}
                >
                  <svg
                    className="w-4 h-4"
                    fill={likeClicked ? "currentColor" : "none"}
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"
                    />
                  </svg>
                </button>

                {/* 싫어요 버튼 */}
                <button
                  onClick={() => {
                    setDislikeClicked(true);
                    setLikeClicked(false);
                    setTimeout(() => setDislikeClicked(false), 2000);
                  }}
                  className={`p-1.5 rounded transition-all duration-300 transform ${
                    dislikeClicked
                      ? "text-red-500 bg-red-100 dark:bg-red-900/30 scale-110 border-2 border-red-300 animate-pulse"
                      : "text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                  }`}
                  title={dislikeClicked ? "싫어요!" : "싫어요"}
                >
                  <svg
                    className="w-4 h-4 rotate-180"
                    fill={dislikeClicked ? "currentColor" : "none"}
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.60L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5"
                    />
                  </svg>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    );
  }
);

export default SimpleChatMessage;

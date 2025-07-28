import { useState, useCallback } from "react";
import { toast } from "react-hot-toast";
import { generateAPI } from "../services/api";

/**
 * 제목 생성 실행 및 결과 폴링을 위한 커스텀 훅
 * @param {string} projectId - 프로젝트 ID
 * @returns {Object} - 제목 생성 관련 상태와 함수들
 */
export const useOrchestration = (projectId) => {
  const [isExecuting, setIsExecuting] = useState(false);
  const [currentExecution, setCurrentExecution] = useState(null);
  const [executionStatus, setExecutionStatus] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);

  /**
   * 제목 생성 실행
   * @param {string} userInput - 사용자 입력
   * @param {Object} options - 추가 옵션 (예: chat_history, useStreaming)
   * @returns {Promise<Object>} - 생성 결과
   */
  const executeOrchestration = useCallback(
    async (userInput, options = {}) => {
      if (!userInput.trim()) {
        toast.error("메시지를 입력해주세요.");
        return null;
      }

      try {
        setIsExecuting(true);
        setExecutionStatus("STARTING");

        // chat_history, prompt_cards, userInput, modelId를 포함하는 data 객체 생성
        const data = {
          userInput: userInput,
          chat_history: options.chat_history || [],
          prompt_cards: options.prompt_cards || [],
          modelId: options.modelId || null,
        };

        console.log("🚀 대화 생성 요청 시작:", {
          projectId,
          inputLength: userInput.length,
          historyLength: data.chat_history.length,
          promptCardsCount: data.prompt_cards.length,
          useStreaming: options.useStreaming === true,
          modelId: data.modelId,
          timestamp: new Date().toISOString(),
        });

        // 🔧 스트리밍 사용 여부 확인 - 더 안전한 로직
        if (options.useStreaming === true) {
          setIsStreaming(true);

          // 스트리밍 콜백 함수 설정
          const onChunk = options.onChunk || (() => {});
          const onError = (error) => {
            console.error("🔧 스트리밍 오류 처리:", error);
            setIsExecuting(false);
            setIsStreaming(false);
            setExecutionStatus("FAILED");

            // 🔧 개선: 오류 타입에 따른 적절한 메시지
            if (
              error.message?.includes("Gateway Timeout") ||
              error.message?.includes("504") ||
              error.code === "ECONNABORTED"
            ) {
              toast.error(
                "서버 응답 시간이 초과되었습니다. 요청을 간단히 하거나 잠시 후 다시 시도해주세요."
              );
            } else if (
              error.message?.includes("CORS") ||
              error.message?.includes("Network Error")
            ) {
              toast.error(
                "서버 연결에 문제가 있습니다. 새로고침 후 다시 시도해주세요."
              );
            } else {
              toast.error(
                "처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
              );
            }

            if (options.onError) options.onError(error);
          };

          const onComplete = (response) => {
            console.log("✅ 스트리밍 완료:", {
              resultLength: response.result?.length || 0,
              timestamp: new Date().toISOString(),
            });
            setIsExecuting(false);
            setIsStreaming(false);
            setExecutionStatus("COMPLETED");
            if (options.onComplete) options.onComplete(response);
          };

          try {
            // 🔧 개선: 스트리밍 API 호출 (내부에서 폴백 처리됨)
            return await generateAPI.generateTitleStream(
              projectId,
              data,
              onChunk,
              onError,
              onComplete
            );
          } catch (streamError) {
            console.error("🔧 스트리밍 최종 실패:", streamError);

            // 🔧 스트리밍 완전 실패 시에도 폴백이 내부에서 처리되므로
            // 여기서는 사용자에게 알림만
            setIsStreaming(false);
            setIsExecuting(false);
            setExecutionStatus("FAILED");

            // 최종 실패 메시지
            toast.error(
              "서비스에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요."
            );
            throw streamError;
          }
        }

        // 🔧 일반 API 호출 (스트리밍 미사용)
        console.log("📄 일반 API 호출 시작...");
        const response = await generateAPI.generateTitle(projectId, data);

        console.log("✅ 대화 생성 완료:", {
          mode: response.mode,
          message: response.message,
          timestamp: new Date().toISOString(),
        });

        setIsExecuting(false);
        setExecutionStatus("COMPLETED");

        return response;
      } catch (error) {
        console.error("❌ 제목 생성 실패:", {
          error: error.message,
          code: error.code,
          status: error.response?.status,
          timestamp: new Date().toISOString(),
        });

        setIsExecuting(false);
        setIsStreaming(false);
        setExecutionStatus("FAILED");

        // 🔧 개선: 상세한 오류 처리
        if (error.response?.status === 504) {
          toast.error(
            "서버 응답 시간이 초과되었습니다. 입력을 간소화하거나 잠시 후 다시 시도해주세요."
          );
        } else if (
          error.message?.includes("CORS") ||
          error.code === "ERR_NETWORK"
        ) {
          toast.error(
            "서버 연결에 문제가 있습니다. 페이지를 새로고침하고 다시 시도해주세요."
          );
        } else if (
          error.response?.status === 400 &&
          error.response?.data?.setup_required
        ) {
          toast.error("프롬프트 카드를 먼저 설정해주세요!");
        } else if (error.code === "ECONNABORTED") {
          toast.error(
            "요청 처리 시간이 초과되었습니다. 입력을 줄이거나 잠시 후 다시 시도해주세요."
          );
        } else if (error.response?.status === 500) {
          toast.error(
            "서버에 일시적인 문제가 있습니다. 잠시 후 다시 시도해주세요."
          );
        } else if (error.response?.status === 403) {
          toast.error("권한이 없습니다. 로그인 상태를 확인해주세요.");
        } else if (error.response?.status === 429) {
          toast.error("요청이 너무 많습니다. 잠시 후 다시 시도해주세요.");
        } else {
          toast.error(
            "처리 중 오류가 발생했습니다. 네트워크 연결을 확인하고 다시 시도해주세요."
          );
        }

        throw error;
      }
    },
    [projectId]
  );

  /**
   * 실행 상태 조회 (Step Functions 사용 시)
   * @param {string} executionArn - 실행 ARN
   * @param {Function} onComplete - 완료 시 콜백
   * @param {Function} onError - 에러 시 콜백
   */
  const pollOrchestrationResult = useCallback(
    async (executionArn, onComplete, onError) => {
      // 스트리밍 모드에서는 폴링이 필요 없음
      if (isStreaming) {
        return;
      }

      const poll = async () => {
        try {
          const result = await generateAPI.getExecutionStatus(executionArn);

          setExecutionStatus(result.status);

          if (result.status === "SUCCEEDED") {
            setIsExecuting(false);
            setExecutionStatus("COMPLETED");

            if (onComplete) {
              onComplete(result);
            }
          } else if (result.status === "FAILED") {
            setIsExecuting(false);
            setExecutionStatus("FAILED");

            if (onError) {
              onError(new Error("처리 실패"));
            }
          } else if (result.status === "RUNNING") {
            // 3초 후 다시 폴링
            setTimeout(poll, 3000);
          }
        } catch (error) {
          console.error("실행 상태 조회 실패:", error);
          setIsExecuting(false);
          setExecutionStatus("FAILED");

          if (onError) {
            onError(error);
          }
        }
      };

      poll();
    },
    [projectId, isStreaming]
  );

  /**
   * 오케스트레이션 상태 초기화
   */
  const resetOrchestration = useCallback(() => {
    setIsExecuting(false);
    setIsStreaming(false);
    setCurrentExecution(null);
    setExecutionStatus(null);
  }, []);

  return {
    isExecuting,
    isStreaming,
    currentExecution,
    executionStatus,
    executeOrchestration,
    pollOrchestrationResult,
    resetOrchestration,
  };
};

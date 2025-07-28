import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * 실시간 사고과정 관리를 위한 커스텀 훅
 */
export const useThinkingProcess = () => {
  const [steps, setSteps] = useState([]);
  const [currentStep, setCurrentStep] = useState(null);
  const [isThinking, setIsThinking] = useState(false);
  const stepIdCounter = useRef(0);
  const stepTimers = useRef(new Map());

  // 새로운 사고 과정 시작
  const startThinking = useCallback(() => {
    setSteps([]);
    setCurrentStep(null);
    setIsThinking(true);
    stepIdCounter.current = 0;
    
    // 기존 타이머들 정리
    stepTimers.current.forEach(timer => clearTimeout(timer));
    stepTimers.current.clear();
  }, []);

  // 사고 과정 종료
  const finishThinking = useCallback(() => {
    setIsThinking(false);
    setCurrentStep(null);
    
    // 모든 활성 단계를 완료로 변경
    setSteps(prevSteps => 
      prevSteps.map(step => 
        step.status === 'active' ? { ...step, status: 'completed' } : step
      )
    );
    
    // 타이머들 정리
    stepTimers.current.forEach(timer => clearTimeout(timer));
    stepTimers.current.clear();
  }, []);

  // 새로운 단계 추가
  const addStep = useCallback((stepConfig) => {
    const stepId = `step_${++stepIdCounter.current}`;
    const newStep = {
      id: stepId,
      type: stepConfig.type || 'processing',
      title: stepConfig.title,
      description: stepConfig.description || '처리 중...',
      status: stepConfig.status || 'active',
      timestamp: new Date(),
      duration: stepConfig.duration,
      progress: stepConfig.progress,
      details: stepConfig.details,
      ...stepConfig
    };

    setSteps(prevSteps => [...prevSteps, newStep]);
    setCurrentStep(stepConfig.type);

    // 자동 완료 타이머 설정 (옵션)
    if (stepConfig.autoComplete) {
      const timer = setTimeout(() => {
        completeStep(stepId, stepConfig.autoComplete.message);
      }, stepConfig.autoComplete.delay || 3000);
      
      stepTimers.current.set(stepId, timer);
    }

    return stepId;
  }, []);

  // 단계 업데이트
  const updateStep = useCallback((stepId, updates) => {
    setSteps(prevSteps =>
      prevSteps.map(step =>
        step.id === stepId ? { ...step, ...updates } : step
      )
    );
  }, []);

  // 단계 완료
  const completeStep = useCallback((stepId, message) => {
    setSteps(prevSteps =>
      prevSteps.map(step =>
        step.id === stepId
          ? {
              ...step,
              status: 'completed',
              description: message || step.description,
              completedAt: new Date()
            }
          : step
      )
    );

    // 타이머 정리
    const timer = stepTimers.current.get(stepId);
    if (timer) {
      clearTimeout(timer);
      stepTimers.current.delete(stepId);
    }
  }, []);

  // 단계 실패
  const failStep = useCallback((stepId, errorMessage) => {
    setSteps(prevSteps =>
      prevSteps.map(step =>
        step.id === stepId
          ? {
              ...step,
              status: 'error',
              description: errorMessage || '오류가 발생했습니다',
              errorAt: new Date()
            }
          : step
      )
    );

    // 타이머 정리
    const timer = stepTimers.current.get(stepId);
    if (timer) {
      clearTimeout(timer);
      stepTimers.current.delete(stepId);
    }
  }, []);

  // 단계 진행률 업데이트
  const updateProgress = useCallback((stepId, progress, message) => {
    updateStep(stepId, {
      progress: Math.min(100, Math.max(0, progress)),
      description: message || `${progress}% 완료`
    });
  }, [updateStep]);

  // 사전 정의된 단계들을 쉽게 추가할 수 있는 헬퍼 함수들
  const addAnalyzingStep = useCallback((title = '질문 분석 중...') => {
    return addStep({
      type: 'analyzing',
      title: '질문 분석',
      description: title,
      autoComplete: {
        delay: 2000,
        message: '질문 분석이 완료되었습니다'
      }
    });
  }, [addStep]);

  const addSearchingStep = useCallback((title = '관련 자료 검색 중...') => {
    return addStep({
      type: 'searching',
      title: '자료 검색',
      description: title
    });
  }, [addStep]);

  const addProcessingStep = useCallback((title = '정보 처리 중...') => {
    return addStep({
      type: 'processing',
      title: '정보 처리',
      description: title
    });
  }, [addStep]);

  const addGeneratingStep = useCallback((title = '답변 생성 중...') => {
    return addStep({
      type: 'generating',
      title: '답변 생성',
      description: title
    });
  }, [addStep]);

  const addReviewingStep = useCallback((title = '내용 검토 중...') => {
    return addStep({
      type: 'reviewing',
      title: '내용 검토',
      description: title,
      autoComplete: {
        delay: 1500,
        message: '내용 검토가 완료되었습니다'
      }
    });
  }, [addStep]);

  // 일반적인 AI 처리 플로우를 자동으로 시작하는 함수
  const startStandardFlow = useCallback((userMessage) => {
    startThinking();
    
    // 표준 플로우 단계들
    setTimeout(() => {
      const analyzingId = addAnalyzingStep(`"${userMessage?.substring(0, 30)}..." 분석 중`);
    }, 100);

    setTimeout(() => {
      addSearchingStep('관련 뉴스 기사 및 데이터 검색 중...');
    }, 2500);

    setTimeout(() => {
      addProcessingStep('수집된 정보를 종합적으로 분석 중...');
    }, 4000);

    setTimeout(() => {
      addGeneratingStep('전문적인 답변을 생성 중...');
    }, 6000);

  }, [startThinking, addAnalyzingStep, addSearchingStep, addProcessingStep, addGeneratingStep]);

  // 컴포넌트 언마운트 시 타이머 정리
  useEffect(() => {
    return () => {
      stepTimers.current.forEach(timer => clearTimeout(timer));
      stepTimers.current.clear();
    };
  }, []);

  return {
    // 상태
    steps,
    currentStep,
    isThinking,
    
    // 기본 제어 함수
    startThinking,
    finishThinking,
    addStep,
    updateStep,
    completeStep,
    failStep,
    updateProgress,
    
    // 헬퍼 함수들
    addAnalyzingStep,
    addSearchingStep, 
    addProcessingStep,
    addGeneratingStep,
    addReviewingStep,
    startStandardFlow,
    
    // 유틸리티
    clearAllSteps: () => setSteps([]),
    getCompletedStepsCount: () => steps.filter(s => s.status === 'completed').length,
    getTotalStepsCount: () => steps.length,
    getProgressPercentage: () => steps.length > 0 ? (steps.filter(s => s.status === 'completed').length / steps.length) * 100 : 0
  };
};
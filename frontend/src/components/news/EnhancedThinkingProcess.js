import React, { useState, useEffect, useRef } from "react";
import { 
  SparklesIcon, 
  MagnifyingGlassIcon,
  DocumentTextIcon,
  CogIcon,
  CheckCircleIcon,
  ExclamationCircleIcon
} from "@heroicons/react/24/outline";

// 단계별 아이콘과 색상 매핑
const STEP_CONFIG = {
  'analyzing': {
    icon: SparklesIcon,
    color: 'from-purple-500 to-pink-500',
    bgColor: 'bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20',
    borderColor: 'border-purple-200 dark:border-purple-700/50',
    label: '질문 분석'
  },
  'searching': {
    icon: MagnifyingGlassIcon,
    color: 'from-blue-500 to-cyan-500',
    bgColor: 'bg-gradient-to-r from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20',
    borderColor: 'border-blue-200 dark:border-blue-700/50',
    label: '자료 검색'
  },
  'processing': {
    icon: CogIcon,
    color: 'from-orange-500 to-red-500',
    bgColor: 'bg-gradient-to-r from-orange-50 to-red-50 dark:from-orange-900/20 dark:to-red-900/20',
    borderColor: 'border-orange-200 dark:border-orange-700/50',
    label: '정보 처리'
  },
  'generating': {
    icon: DocumentTextIcon,
    color: 'from-green-500 to-emerald-500',
    bgColor: 'bg-gradient-to-r from-green-50 to-emerald-50 dark:from-green-900/20 dark:to-emerald-900/20',
    borderColor: 'border-green-200 dark:border-green-700/50',
    label: '답변 생성'
  },
  'completed': {
    icon: CheckCircleIcon,
    color: 'from-emerald-500 to-teal-500',
    bgColor: 'bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20',
    borderColor: 'border-emerald-200 dark:border-emerald-700/50',
    label: '완료'
  }
};

// 타이핑 효과 컴포넌트
const TypingText = ({ text, speed = 30, onComplete }) => {
  const [displayedText, setDisplayedText] = useState('');
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (currentIndex < text.length) {
      const timer = setTimeout(() => {
        setDisplayedText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, speed);
      return () => clearTimeout(timer);
    } else if (onComplete) {
      onComplete();
    }
  }, [currentIndex, text, speed, onComplete]);

  useEffect(() => {
    setDisplayedText('');
    setCurrentIndex(0);
  }, [text]);

  return (
    <span className="inline-flex items-center">
      {displayedText}
      {currentIndex < text.length && (
        <span className="inline-block w-0.5 h-4 bg-current animate-pulse ml-1" />
      )}
    </span>
  );
};

// 개별 사고 단계 컴포넌트
const ThinkingStep = ({ step, isActive, isCompleted, onComplete }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showDetails, setShowDetails] = useState(false);
  const stepConfig = STEP_CONFIG[step.type] || STEP_CONFIG['processing'];
  const IconComponent = stepConfig.icon;

  useEffect(() => {
    if (isActive) {
      setIsExpanded(true);
      setTimeout(() => setShowDetails(true), 300);
    }
  }, [isActive]);

  const handleTypingComplete = () => {
    if (isActive && onComplete) {
      setTimeout(() => {
        onComplete();
      }, 1000);
    }
  };

  return (
    <div className={`
      transition-all duration-700 ease-out transform
      ${isExpanded ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-95 translate-y-4'}
      ${isActive ? 'ring-2 ring-offset-2 ring-offset-white dark:ring-offset-gray-900' : ''}
    `}>
      <div className={`
        rounded-xl border ${stepConfig.borderColor} ${stepConfig.bgColor}
        p-4 transition-all duration-500
        ${isActive ? 'shadow-lg shadow-current/20 scale-[1.02]' : 'shadow-sm'}
        ${isCompleted ? 'ring-1 ring-emerald-200 dark:ring-emerald-700/50' : ''}
      `}>
        <div className="flex items-center gap-4">
          {/* 아이콘 영역 */}
          <div className="relative">
            <div className={`
              w-12 h-12 rounded-full flex items-center justify-center
              bg-gradient-to-r ${stepConfig.color} text-white
              transition-all duration-500
              ${isActive ? 'scale-110 shadow-lg' : 'scale-100'}
            `}>
              <IconComponent className="w-6 h-6" />
              
              {/* 활성 상태 펄스 효과 */}
              {isActive && !isCompleted && (
                <div className={`
                  absolute inset-0 rounded-full
                  bg-gradient-to-r ${stepConfig.color} opacity-75
                  animate-ping
                `} />
              )}
              
              {/* 완료 체크마크 오버레이 */}
              {isCompleted && (
                <div className="absolute inset-0 rounded-full bg-emerald-500 flex items-center justify-center animate-bounce">
                  <CheckCircleIcon className="w-6 h-6 text-white" />
                </div>
              )}
            </div>
          </div>

          {/* 내용 영역 */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-2">
              <h3 className={`
                font-semibold text-lg
                bg-gradient-to-r ${stepConfig.color} bg-clip-text text-transparent
              `}>
                {step.title || stepConfig.label}
              </h3>
              
              {/* 진행률 표시 */}
              {step.progress !== undefined && !isCompleted && (
                <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
                  <div className="w-16 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className={`h-full bg-gradient-to-r ${stepConfig.color} transition-all duration-700 ease-out`}
                      style={{ width: `${step.progress}%` }}
                    />
                  </div>
                  <span className="font-mono text-xs">{step.progress}%</span>
                </div>
              )}
            </div>

            {/* 설명 텍스트 */}
            {showDetails && (
              <div className="text-gray-700 dark:text-gray-300 leading-relaxed">
                {isActive && !isCompleted ? (
                  <TypingText 
                    text={step.description || '처리 중...'}
                    speed={20}
                    onComplete={handleTypingComplete}
                  />
                ) : (
                  <span>{step.description || '처리 완료'}</span>
                )}
              </div>
            )}

            {/* 세부 정보 */}
            {step.details && showDetails && (
              <div className="mt-3 p-3 rounded-lg bg-white/50 dark:bg-gray-800/50 border border-gray-200/50 dark:border-gray-700/50">
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  {Array.isArray(step.details) ? (
                    <ul className="space-y-1">
                      {step.details.map((detail, i) => (
                        <li key={i} className="flex items-center gap-2">
                          <div className="w-1 h-1 bg-current rounded-full opacity-60" />
                          {detail}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>{step.details}</p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const EnhancedThinkingProcess = ({ 
  steps = [], 
  currentStep = null, 
  isVisible = true,
  onToggle = null 
}) => {
  const [isMinimized, setIsMinimized] = useState(false);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [completedSteps, setCompletedSteps] = useState(new Set());
  const containerRef = useRef(null);

  // 활성 단계 관리
  useEffect(() => {
    const activeIndex = steps.findIndex(step => step.status === 'active');
    if (activeIndex !== -1) {
      setActiveStepIndex(activeIndex);
    }
  }, [steps]);

  // 단계 완료 처리
  const handleStepComplete = (stepIndex) => {
    setCompletedSteps(prev => new Set([...prev, stepIndex]));
    
    // 다음 단계로 이동
    if (stepIndex < steps.length - 1) {
      setTimeout(() => {
        setActiveStepIndex(stepIndex + 1);
      }, 500);
    }
  };

  const handleToggle = () => {
    setIsMinimized(!isMinimized);
    if (onToggle) onToggle(!isMinimized);
  };

  if (!isVisible || steps.length === 0) return null;

  const completedCount = steps.filter(s => s.status === 'completed').length;
  const totalCount = steps.length;
  const progressPercentage = (completedCount / totalCount) * 100;

  return (
    <div 
      ref={containerRef}
      className="mb-6 transform transition-all duration-700 ease-out"
      style={{
        animation: 'slideInFromBottom 0.7s ease-out'
      }}
    >
      {/* 메인 컨테이너 */}
      <div className="relative">
        {/* 글로우 효과 배경 */}
        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/10 via-purple-500/10 to-pink-500/10 rounded-2xl blur-xl" />
        
        <div className="relative bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm rounded-2xl border border-gray-200/50 dark:border-gray-700/50 shadow-xl">
          {/* 헤더 */}
          <button
            onClick={handleToggle}
            className="w-full px-6 py-4 flex items-center justify-between text-left hover:bg-gray-50/50 dark:hover:bg-gray-800/50 transition-all duration-300 rounded-t-2xl group"
          >
            <div className="flex items-center gap-4">
              {/* 메인 아이콘 */}
              <div className="relative">
                <div className="w-10 h-10 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 flex items-center justify-center">
                  <SparklesIcon className="w-5 h-5 text-white" />
                </div>
                {currentStep && (
                  <div className="absolute -top-1 -right-1 w-4 h-4 bg-emerald-500 rounded-full animate-bounce" />
                )}
              </div>
              
              <div>
                <h2 className="text-lg font-bold bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-300 bg-clip-text text-transparent">
                  AI 사고 과정 ✨
                </h2>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {currentStep ? `현재: ${STEP_CONFIG[currentStep]?.label || currentStep}` : '분석 완료'}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-4">
              {/* 전체 진행률 */}
              <div className="hidden sm:flex items-center gap-3">
                <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-1000 ease-out"
                    style={{ width: `${progressPercentage}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-600 dark:text-gray-400 min-w-0">
                  {completedCount}/{totalCount}
                </span>
              </div>
              
              {/* 토글 아이콘 */}
              <div className={`
                w-6 h-6 flex items-center justify-center transition-transform duration-300
                ${isMinimized ? 'rotate-180' : ''}
              `}>
                <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          </button>

          {/* 내용 영역 */}
          {!isMinimized && (
            <div className="px-6 pb-6 space-y-4">
              {steps.map((step, index) => (
                <ThinkingStep
                  key={step.id || index}
                  step={step}
                  isActive={index === activeStepIndex && step.status === 'active'}
                  isCompleted={completedSteps.has(index) || step.status === 'completed'}
                  onComplete={() => handleStepComplete(index)}
                />
              ))}
              
              {/* 완료 메시지 */}
              {completedCount === totalCount && totalCount > 0 && (
                <div className="mt-6 p-4 rounded-xl bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 border border-emerald-200 dark:border-emerald-700/50">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-full flex items-center justify-center animate-pulse">
                      <CheckCircleIcon className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-emerald-800 dark:text-emerald-200">
                        모든 분석이 완료되었습니다! 🎉
                      </p>
                      <p className="text-sm text-emerald-600 dark:text-emerald-300">
                        이제 전문적인 답변을 확인하세요.
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* 커스텀 CSS 애니메이션 */}
      <style jsx>{`
        @keyframes slideInFromBottom {
          from {
            opacity: 0;
            transform: translateY(20px) scale(0.95);
          }
          to {
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
      `}</style>
    </div>
  );
};

export default EnhancedThinkingProcess;
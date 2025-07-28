import React, { useState, useEffect } from "react";
import { 
  SparklesIcon, 
  MagnifyingGlassIcon,
  DocumentTextIcon,
  CogIcon,
  CheckCircleIcon,
  ExclamationCircleIcon,
  ClockIcon
} from "@heroicons/react/24/outline";

// 사고 과정 단계별 아이콘 매핑
const STEP_ICONS = {
  'analyzing': MagnifyingGlassIcon,
  'searching': MagnifyingGlassIcon, 
  'processing': CogIcon,
  'generating': SparklesIcon,
  'reviewing': DocumentTextIcon,
  'completed': CheckCircleIcon,
  'error': ExclamationCircleIcon,
  'waiting': ClockIcon
};

// 단계별 한국어 표시명
const STEP_LABELS = {
  'analyzing': '질문 분석',
  'searching': '자료 검색',
  'processing': '정보 처리', 
  'generating': '답변 생성',
  'reviewing': '내용 검토',
  'completed': '완료',
  'error': '오류',
  'waiting': '대기'
};

const RealTimeThinking = ({ 
  steps = [], 
  currentStep = null, 
  isVisible = true,
  onToggle = null
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [animatingSteps, setAnimatingSteps] = useState(new Set());

  // 새로운 단계가 추가될 때 애니메이션 효과
  useEffect(() => {
    if (steps.length > 0) {
      const latestStep = steps[steps.length - 1];
      if (latestStep.status === 'active' || latestStep.status === 'processing') {
        setAnimatingSteps(prev => new Set([...prev, latestStep.id]));
        
        // 2초 후 애니메이션 제거
        setTimeout(() => {
          setAnimatingSteps(prev => {
            const newSet = new Set(prev);
            newSet.delete(latestStep.id);
            return newSet;
          });
        }, 2000);
      }
    }
  }, [steps]);

  if (!isVisible || steps.length === 0) return null;

  const handleToggle = () => {
    setIsExpanded(!isExpanded);
    if (onToggle) onToggle(!isExpanded);
  };

  const getStepStatus = (step) => {
    if (step.status === 'completed') return 'completed';
    if (step.status === 'error') return 'error';
    if (step.status === 'active' || step.status === 'processing') return 'active';
    return 'waiting';
  };

  const getStepIcon = (step) => {
    const status = getStepStatus(step);
    const IconComponent = STEP_ICONS[step.type] || STEP_ICONS[status] || CogIcon;
    return IconComponent;
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return 'text-green-500';
      case 'error': return 'text-red-500';
      case 'active': return 'text-blue-500';
      default: return 'text-gray-400';
    }
  };

  const getStatusBgColor = (status) => {
    switch (status) {
      case 'completed': return 'bg-green-500';
      case 'error': return 'bg-red-500';
      case 'active': return 'bg-blue-500';
      default: return 'bg-gray-300';
    }
  };

  return (
    <div className="mb-4 border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-gradient-to-r from-blue-50 to-purple-50 dark:from-gray-800 dark:to-gray-800/50">
      {/* 헤더 */}
      <button
        onClick={handleToggle}
        className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-white/50 dark:hover:bg-gray-700/30 transition-all duration-200"
      >
        <div className="flex items-center gap-3">
          <div className="relative">
            <SparklesIcon className="w-5 h-5 text-blue-500" />
            {currentStep && (
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-blue-500 rounded-full animate-pulse" />
            )}
          </div>
          <div>
            <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">
              AI 사고 과정
            </span>
            <div className="text-xs text-gray-600 dark:text-gray-400">
              {currentStep ? `현재: ${STEP_LABELS[currentStep] || currentStep}` : '분석 완료'}
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {steps.filter(s => s.status === 'completed').length}/{steps.length}
          </div>
          <svg
            className={`w-4 h-4 text-gray-500 transition-transform duration-200 ${
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
        </div>
      </button>

      {/* 내용 */}
      {isExpanded && (
        <div className="px-4 pb-4">
          <div className="space-y-3">
            {steps.map((step, index) => {
              const status = getStepStatus(step);
              const IconComponent = getStepIcon(step);
              const isAnimating = animatingSteps.has(step.id);
              
              return (
                <div 
                  key={step.id || index}
                  className={`flex items-start gap-3 p-3 rounded-lg transition-all duration-300 ${
                    isAnimating ? 'bg-blue-50 dark:bg-blue-900/20 scale-102' : 'bg-white/50 dark:bg-gray-700/30'
                  }`}
                >
                  {/* 아이콘 및 상태 */}
                  <div className="flex-shrink-0 relative">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${getStatusBgColor(status)} transition-colors duration-200`}>
                      <IconComponent className="w-4 h-4 text-white" />
                    </div>
                    
                    {/* 로딩 애니메이션 */}
                    {status === 'active' && (
                      <div className="absolute inset-0 w-8 h-8 rounded-full border-2 border-blue-200 border-t-blue-500 animate-spin" />
                    )}
                  </div>

                  {/* 내용 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="text-sm font-medium text-gray-800 dark:text-gray-200">
                        {step.title || STEP_LABELS[step.type] || `단계 ${index + 1}`}
                      </h4>
                      {step.duration && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          ({step.duration}ms)
                        </span>
                      )}
                    </div>
                    
                    <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                      {step.description || step.message || '처리 중...'}
                    </p>
                    
                    {/* 진행률 표시 (선택적) */}
                    {step.progress !== undefined && status === 'active' && (
                      <div className="mt-2">
                        <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-1.5">
                          <div 
                            className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                            style={{ width: `${step.progress}%` }}
                          />
                        </div>
                        <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                          {step.progress}% 완료
                        </div>
                      </div>
                    )}
                    
                    {/* 세부 정보 (선택적) */}
                    {step.details && (
                      <div className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                        {Array.isArray(step.details) ? (
                          <ul className="list-disc list-inside space-y-1">
                            {step.details.map((detail, i) => (
                              <li key={i}>{detail}</li>
                            ))}
                          </ul>
                        ) : (
                          <p>{step.details}</p>
                        )}
                      </div>
                    )}
                  </div>

                  {/* 상태 표시 */}
                  <div className="flex-shrink-0">
                    {status === 'completed' && (
                      <CheckCircleIcon className="w-5 h-5 text-green-500" />
                    )}
                    {status === 'error' && (
                      <ExclamationCircleIcon className="w-5 h-5 text-red-500" />
                    )}
                    {status === 'active' && (
                      <div className="w-5 h-5 flex items-center justify-center">
                        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
          
          {/* 전체 진행률 */}
          {steps.length > 0 && (
            <div className="mt-4 pt-3 border-t border-gray-200 dark:border-gray-600">
              <div className="flex justify-between items-center text-xs text-gray-600 dark:text-gray-400 mb-2">
                <span>전체 진행률</span>
                <span>{Math.round((steps.filter(s => s.status === 'completed').length / steps.length) * 100)}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2">
                <div 
                  className="bg-gradient-to-r from-blue-500 to-purple-500 h-2 rounded-full transition-all duration-500"
                  style={{ 
                    width: `${(steps.filter(s => s.status === 'completed').length / steps.length) * 100}%` 
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RealTimeThinking;
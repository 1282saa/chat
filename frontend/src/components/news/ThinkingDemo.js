import React, { useState } from 'react';
import RealTimeThinking from './RealTimeThinking';
import { useThinkingProcess } from '../../hooks/useThinkingProcess';
import { PlayIcon, StopIcon } from '@heroicons/react/24/outline';

/**
 * 실시간 사고과정 표시 기능을 데모하는 컴포넌트
 * 개발 및 테스트 용도로 사용
 */
const ThinkingDemo = () => {
  const [demoInput, setDemoInput] = useState('');
  
  const {
    steps,
    currentStep,
    isThinking,
    startThinking,
    finishThinking,
    addAnalyzingStep,
    addSearchingStep,
    addProcessingStep,
    addGeneratingStep,
    addReviewingStep,
    completeStep,
    updateProgress
  } = useThinkingProcess();

  const startDemo = async () => {
    if (!demoInput.trim()) return;
    
    startThinking();
    
    // 1단계: 질문 분석
    const step1 = addAnalyzingStep(`"${demoInput}" 질문 분석 중...`);
    
    setTimeout(() => {
      completeStep(step1, '질문 분석 완료 - 경제 뉴스 관련 키워드 추출');
      
      // 2단계: 자료 검색
      const step2 = addSearchingStep('관련 뉴스 기사 검색 중...');
      
      setTimeout(() => {
        updateProgress(step2, 50, '50개 기사 발견 - 필터링 중...');
        
        setTimeout(() => {
          completeStep(step2, '15개의 관련 기사 선별 완료');
          
          // 3단계: 정보 처리
          const step3 = addProcessingStep('수집된 정보 분석 및 종합 중...');
          
          setTimeout(() => {
            updateProgress(step3, 75, '주요 내용 추출 중...');
            
            setTimeout(() => {
              completeStep(step3, '핵심 정보 종합 및 분석 완료');
              
              // 4단계: 답변 생성
              const step4 = addGeneratingStep('전문적인 답변 생성 중...');
              
              setTimeout(() => {
                updateProgress(step4, 30, '구조화된 답변 작성 중...');
                
                setTimeout(() => {
                  updateProgress(step4, 70, '인용 정보 추가 중...');
                  
                  setTimeout(() => {
                    completeStep(step4, '답변 생성 완료');
                    
                    // 5단계: 검토
                    const step5 = addReviewingStep('내용 정확성 검토 중...');
                    
                    setTimeout(() => {
                      completeStep(step5, '최종 검토 완료');
                      
                      // 모든 과정 완료
                      setTimeout(() => {
                        finishThinking();
                      }, 1000);
                    }, 1500);
                  }, 1200);
                }, 1000);
              }, 800);
            }, 1500);
          }, 1200);
        }, 1000);
      }, 800);
    }, 2000);
  };

  const stopDemo = () => {
    finishThinking();
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
        <h2 className="text-xl font-semibold text-gray-800 dark:text-white mb-4">
          🧠 AI 사고과정 표시 데모
        </h2>
        
        <p className="text-gray-600 dark:text-gray-300 mb-6">
          사용자가 질문을 하면 AI가 어떤 과정을 거쳐 답변을 생성하는지 실시간으로 확인할 수 있습니다.
        </p>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              테스트 질문 입력
            </label>
            <input
              type="text"
              value={demoInput}
              onChange={(e) => setDemoInput(e.target.value)}
              placeholder="예: 최근 한국 경제 동향은 어떤가요?"
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
              disabled={isThinking}
            />
          </div>
          
          <div className="flex gap-3">
            {!isThinking ? (
              <button
                onClick={startDemo}
                disabled={!demoInput.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg transition-colors duration-200"
              >
                <PlayIcon className="w-4 h-4" />
                사고과정 시뮬레이션 시작
              </button>
            ) : (
              <button
                onClick={stopDemo}
                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors duration-200"
              >
                <StopIcon className="w-4 h-4" />
                중지
              </button>
            )}
          </div>
          
          {/* 진행 상태 표시 */}
          {isThinking && (
            <div className="text-sm text-gray-600 dark:text-gray-400">
              💭 현재 단계: <strong>{currentStep || '준비 중'}</strong>
            </div>
          )}
        </div>
      </div>
      
      {/* 실시간 사고과정 표시 */}
      {steps.length > 0 && (
        <RealTimeThinking
          steps={steps}
          currentStep={currentStep}
          isVisible={true}
        />
      )}
      
      {/* 완료 메시지 */}
      {!isThinking && steps.length > 0 && steps.every(s => s.status === 'completed') && (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <span className="text-sm font-medium text-green-800 dark:text-green-200">
              모든 사고과정이 완료되었습니다! 이제 답변이 표시됩니다.
            </span>
          </div>
        </div>
      )}
      
      {/* 사용법 안내 */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-200 mb-2">
          💡 기능 설명
        </h3>
        <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
          <li>• <strong>질문 분석:</strong> 사용자 질문의 의도와 키워드를 파악합니다</li>
          <li>• <strong>자료 검색:</strong> 관련 뉴스 기사와 데이터를 검색합니다</li>
          <li>• <strong>정보 처리:</strong> 수집된 정보를 분석하고 종합합니다</li>
          <li>• <strong>답변 생성:</strong> 체계적이고 전문적인 답변을 작성합니다</li>
          <li>• <strong>내용 검토:</strong> 최종 검토를 통해 정확성을 확인합니다</li>
        </ul>
      </div>
    </div>
  );
};

export default ThinkingDemo;
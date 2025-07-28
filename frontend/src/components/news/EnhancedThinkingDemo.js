import React, { useState } from 'react';
import EnhancedThinkingProcess from './EnhancedThinkingProcess';
import { useThinkingProcess } from '../../hooks/useThinkingProcess';
import { PlayIcon, StopIcon, SparklesIcon } from '@heroicons/react/24/outline';

/**
 * 향상된 실시간 사고과정 표시 기능을 데모하는 컴포넌트
 * ChatGPT 스타일의 우아한 애니메이션과 타이핑 효과 포함
 */
const EnhancedThinkingDemo = () => {
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
    updateProgress,
    addStep
  } = useThinkingProcess();

  const startEnhancedDemo = async () => {
    if (!demoInput.trim()) return;
    
    startThinking();
    
    // 1단계: 질문 분석 (ChatGPT 스타일)
    const step1 = addStep({
      type: 'analyzing',
      title: '질문 의도 파악',
      description: `"${demoInput.substring(0, 50)}..." 질문을 심층 분석하여 핵심 키워드와 사용자 의도를 파악하고 있습니다.`,
      status: 'active',
      details: [
        '자연어 처리를 통한 의미 분석',
        '핵심 키워드 추출 및 가중치 계산',
        '질문 유형 분류 및 답변 전략 수립'
      ]
    });
    
    setTimeout(() => {
      completeStep(step1, '질문 분석 완료 - 경제 뉴스 관련 키워드 추출 및 검색 전략 수립');
      
      // 2단계: 자료 검색
      const step2 = addStep({
        type: 'searching',
        title: '관련 데이터 검색',
        description: '서울경제신문 데이터베이스에서 관련 뉴스 기사를 검색하고 있습니다.',
        status: 'active',
        progress: 0,
        details: [
          '실시간 뉴스 데이터베이스 탐색',
          'AI 기반 유사도 매칭',
          '신뢰도 높은 출처 우선 선별'
        ]
      });
      
      // 진행률 애니메이션
      let progress = 0;
      const progressInterval = setInterval(() => {
        progress += 15;
        updateProgress(step2, progress, `${Math.min(progress * 2, 100)}개 기사 검색 중... (${progress}%)`);
        
        if (progress >= 100) {
          clearInterval(progressInterval);
          setTimeout(() => {
            completeStep(step2, '18개의 관련 기사 선별 완료 - 최신성과 신뢰도 기준으로 필터링');
            
            // 3단계: 정보 처리
            const step3 = addStep({
              type: 'processing',
              title: '정보 종합 분석',
              description: '수집된 정보를 AI가 종합적으로 분석하여 핵심 인사이트를 추출하고 있습니다.',
              status: 'active',
              details: [
                '다중 소스 교차 검증',
                '팩트 체크 및 정확성 검토',
                '핵심 논점 및 트렌드 분석'
              ]
            });
            
            setTimeout(() => {
              updateProgress(step3, 75, '핵심 정보 추출 및 논리적 구조화 진행 중...');
              
              setTimeout(() => {
                completeStep(step3, '정보 분석 완료 - 체계적인 논리 구조와 핵심 인사이트 도출');
                
                // 4단계: 답변 생성
                const step4 = addStep({
                  type: 'generating',
                  title: '전문적 답변 생성',
                  description: '분석된 정보를 바탕으로 전문적이고 이해하기 쉬운 답변을 생성하고 있습니다.',
                  status: 'active',
                  details: [
                    '논리적 구조로 답변 구성',
                    '전문 용어 해설 및 예시 추가',
                    '신뢰할 수 있는 출처 인용 정보 포함'
                  ]
                });
                
                setTimeout(() => {
                  updateProgress(step4, 40, '구조화된 답변 작성 중...');
                  
                  setTimeout(() => {
                    updateProgress(step4, 80, '인용 정보 및 출처 추가 중...');
                    
                    setTimeout(() => {
                      completeStep(step4, '답변 생성 완료 - 전문적이고 신뢰할 수 있는 콘텐츠 완성');
                      
                      // 5단계: 최종 검토
                      const step5 = addStep({
                        type: 'completed',
                        title: '품질 검증',
                        description: '생성된 답변의 정확성과 완전성을 최종 검토하고 있습니다.',
                        status: 'active',
                        details: [
                          '팩트 체크 및 정확성 재검증',
                          '가독성 및 이해도 평가',
                          '출처 정보 유효성 확인'
                        ]
                      });
                      
                      setTimeout(() => {
                        completeStep(step5, '모든 검토 완료 - 높은 품질의 답변이 준비되었습니다');
                        
                        // 모든 과정 완료
                        setTimeout(() => {
                          finishThinking();
                        }, 1500);
                      }, 2000);
                    }, 1500);
                  }, 1200);
                }, 1000);
              }, 2000);
            }, 1800);
          }, 1000);
        }
      }, 200);
    }, 2500);
  };

  const stopDemo = () => {
    finishThinking();
  };

  return (
    <div className="max-w-5xl mx-auto p-6 space-y-8">
      {/* 헤더 섹션 */}
      <div className="text-center">
        <div className="inline-flex items-center gap-3 mb-4">
          <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-500 rounded-2xl flex items-center justify-center">
            <SparklesIcon className="w-6 h-6 text-white" />
          </div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-300 bg-clip-text text-transparent">
            Enhanced AI 사고과정 ✨
          </h1>
        </div>
        <p className="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
          ChatGPT 스타일의 우아한 애니메이션과 실시간 타이핑 효과로 
          AI의 사고 과정을 생생하게 경험해보세요.
        </p>
      </div>

      {/* 컨트롤 섹션 */}
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl border border-gray-200/50 dark:border-gray-700/50 p-6">
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
              🤔 AI에게 질문해보세요
            </label>
            <input
              type="text"
              value={demoInput}
              onChange={(e) => setDemoInput(e.target.value)}
              placeholder="예: 최근 한국 경제 동향과 주요 이슈들을 분석해주세요"
              className="w-full px-4 py-3 border border-gray-300 dark:border-gray-600 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 transition-all duration-200"
              disabled={isThinking}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !isThinking && demoInput.trim()) {
                  startEnhancedDemo();
                }
              }}
            />
          </div>
          
          <div className="flex items-center gap-4">
            {!isThinking ? (
              <button
                onClick={startEnhancedDemo}
                disabled={!demoInput.trim()}
                className="flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-400 disabled:to-gray-500 text-white rounded-xl font-semibold transition-all duration-200 transform hover:scale-105 disabled:scale-100 shadow-lg disabled:shadow-none"
              >
                <PlayIcon className="w-5 h-5" />
                Enhanced 사고과정 시작
              </button>
            ) : (
              <button
                onClick={stopDemo}
                className="flex items-center gap-3 px-6 py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white rounded-xl font-semibold transition-all duration-200 transform hover:scale-105 shadow-lg"
              >
                <StopIcon className="w-5 h-5" />
                중지
              </button>
            )}
            
            {/* 상태 표시 */}
            {isThinking && (
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                <span className="font-medium">
                  현재: <strong className="text-blue-600 dark:text-blue-400">
                    {currentStep || '준비 중'}
                  </strong>
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* 실시간 사고과정 표시 */}
      {steps.length > 0 && (
        <EnhancedThinkingProcess
          steps={steps}
          currentStep={currentStep}
          isVisible={true}
        />
      )}
      
      {/* 기능 설명 섹션 */}
      <div className="grid md:grid-cols-3 gap-6">
        <div className="bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 p-6 rounded-2xl border border-purple-200 dark:border-purple-700/50">
          <div className="w-10 h-10 bg-gradient-to-r from-purple-500 to-pink-500 rounded-xl flex items-center justify-center mb-4">
            <span className="text-white font-bold">✨</span>
          </div>
          <h3 className="text-lg font-semibold text-purple-800 dark:text-purple-200 mb-2">
            실시간 타이핑 효과
          </h3>
          <p className="text-purple-600 dark:text-purple-300 text-sm">
            ChatGPT처럼 텍스트가 실시간으로 타이핑되는 생동감 있는 효과
          </p>
        </div>
        
        <div className="bg-gradient-to-br from-blue-50 to-cyan-50 dark:from-blue-900/20 dark:to-cyan-900/20 p-6 rounded-2xl border border-blue-200 dark:border-blue-700/50">
          <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center mb-4">
            <span className="text-white font-bold">🎨</span>
          </div>
          <h3 className="text-lg font-semibold text-blue-800 dark:text-blue-200 mb-2">
            우아한 애니메이션
          </h3>
          <p className="text-blue-600 dark:text-blue-300 text-sm">
            부드러운 전환 효과와 펄스 애니메이션으로 프리미엄 경험 제공
          </p>
        </div>
        
        <div className="bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 p-6 rounded-2xl border border-emerald-200 dark:border-emerald-700/50">
          <div className="w-10 h-10 bg-gradient-to-r from-emerald-500 to-teal-500 rounded-xl flex items-center justify-center mb-4">
            <span className="text-white font-bold">⚡</span>
          </div>
          <h3 className="text-lg font-semibold text-emerald-800 dark:text-emerald-200 mb-2">
            단계별 시각화
          </h3>
          <p className="text-emerald-600 dark:text-emerald-300 text-sm">
            각 처리 단계를 직관적인 아이콘과 색상으로 명확하게 구분
          </p>
        </div>
      </div>
    </div>
  );
};

export default EnhancedThinkingDemo;
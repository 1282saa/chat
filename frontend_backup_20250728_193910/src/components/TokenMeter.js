/*
토큰 미터 컴포넌트
현재 토큰 사용량, 최대 한도, 예상 비용을 시각적으로 표시

🔄 PRESERVED FOR FUTURE USE
이 컴포넌트는 현재 사용되지 않지만 향후 ChatWindow에 토큰 사용량 표시 기능 추가 시 활용 예정
사용법: <TokenMeter totalTokens={1500} maxTokens={8000} cost={0.02} />
*/

import React from "react";

const TokenMeter = ({ totalTokens, maxTokens = 8000, cost = 0 }) => {
  const percentage = Math.min((totalTokens / maxTokens) * 100, 100);

  // 색상 결정 로직
  const getProgressColor = () => {
    if (percentage < 50) return "bg-green-500";
    if (percentage < 80) return "bg-yellow-500";
    return "bg-red-500";
  };

  const getTextColor = () => {
    if (percentage < 50) return "text-green-600";
    if (percentage < 80) return "text-yellow-600";
    return "text-red-600";
  };

  // 숫자 포맷팅
  const formatNumber = (num) => {
    if (num >= 1000) {
      return (num / 1000).toFixed(1) + "K";
    }
    return num.toLocaleString();
  };

  const formatCost = (cost) => {
    if (cost < 0.01) {
      return "< $0.01";
    }
    return `$${cost.toFixed(3)}`;
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900">토큰 사용량</h3>
        <p className="text-sm text-gray-500 mt-1">
          현재 프롬프트의 예상 토큰 수와 비용
        </p>
      </div>

      <div className="p-4">
        {/* 토큰 수 표시 */}
        <div className="flex justify-between items-center mb-3">
          <span className="text-sm font-medium text-gray-700">토큰 수</span>
          <span className={`text-lg font-bold ${getTextColor()}`}>
            {formatNumber(totalTokens)} / {formatNumber(maxTokens)}
          </span>
        </div>

        {/* 프로그레스 바 */}
        <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
          <div
            className={`h-3 rounded-full transition-all duration-300 ${getProgressColor()}`}
            style={{ width: `${percentage}%` }}
          />
        </div>

        {/* 퍼센트 표시 */}
        <div className="flex justify-between items-center mb-4">
          <span className="text-sm text-gray-600">사용률</span>
          <span className={`text-sm font-semibold ${getTextColor()}`}>
            {percentage.toFixed(1)}%
          </span>
        </div>

        {/* 예상 비용 */}
        <div className="border-t border-gray-200 pt-4">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-gray-700">예상 비용</span>
            <span className="text-lg font-bold text-blue-600">
              {formatCost(cost)}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            Claude 3.5 Sonnet (APAC) 기준 (Input: $3/1M tokens)
          </p>
        </div>

        {/* 경고 메시지 */}
        {percentage > 80 && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-yellow-400"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-yellow-800">
                  높은 토큰 사용량
                </h3>
                <div className="mt-2 text-sm text-yellow-700">
                  <p>
                    토큰 사용량이 높습니다. 일부 카드를 비활성화하거나 내용을
                    축약하는 것을 고려해보세요.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {percentage >= 100 && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-red-400"
                  viewBox="0 0 20 20"
                  fill="currentColor"
                >
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  토큰 한도 초과
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  <p>
                    최대 토큰 한도를 초과했습니다. 일부 카드를 비활성화해야
                    합니다.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 토큰 절약 팁 */}
        {totalTokens > 0 && (
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
            <h4 className="text-sm font-medium text-blue-800 mb-2">
              토큰 절약 팁
            </h4>
            <ul className="text-xs text-blue-700 space-y-1">
              <li>• 불필요한 카드는 비활성화하세요</li>
              <li>• 긴 설명보다 핵심 내용 위주로 작성하세요</li>
              <li>• 중복되는 내용은 하나의 카드로 통합하세요</li>
              <li>• Placeholder를 활용해 동적 내용을 줄이세요</li>
            </ul>
          </div>
        )}
      </div>
    </div>
  );
};

export default TokenMeter;

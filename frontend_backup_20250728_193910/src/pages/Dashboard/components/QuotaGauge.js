import React from 'react';
import { RadialBarChart, RadialBar, ResponsiveContainer } from 'recharts';

const QuotaGauge = ({ used, limit }) => {
  const percentage = (used / limit) * 100;
  const data = [
    {
      name: '사용량',
      value: percentage,
      fill: percentage >= 80 ? '#f97316' : '#3b82f6', // orange-500 or blue-500
    },
  ];

  const formatNumber = (num) => {
    if (num >= 1000000) {
      return `${(num / 1000000).toFixed(1)}M`;
    } else if (num >= 1000) {
      return `${(num / 1000).toFixed(1)}K`;
    }
    return num.toString();
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm p-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">월간 토큰 한도</h3>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {formatNumber(used)} / {formatNumber(limit)} 토큰 사용됨
        </p>
      </div>
      
      <div className="relative h-48">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="60%"
            outerRadius="90%"
            data={data}
            startAngle={90}
            endAngle={-270}
          >
            <RadialBar
              dataKey="value"
              cornerRadius={10}
              fill={data[0].fill}
            />
          </RadialBarChart>
        </ResponsiveContainer>
        
        {/* Center text */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <div className={`text-2xl font-bold ${
              percentage >= 80 
                ? 'text-orange-600 dark:text-orange-400' 
                : 'text-blue-600 dark:text-blue-400'
            }`}>
              {percentage.toFixed(1)}%
            </div>
            <div className="text-sm text-gray-500 dark:text-gray-400">사용됨</div>
          </div>
        </div>
      </div>

      {/* Progress indicator */}
      <div className="mt-4">
        <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400 mb-2">
          <span>0</span>
          <span>{formatNumber(limit)}</span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-300 ${
              percentage >= 80 
                ? 'bg-orange-500' 
                : 'bg-blue-500'
            }`}
            style={{ width: `${Math.min(percentage, 100)}%` }}
          ></div>
        </div>
      </div>

      {percentage >= 80 && (
        <div className="mt-3 p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
          <p className="text-sm text-orange-800 dark:text-orange-200">
            ⚠️ 토큰 사용량이 80%를 초과했습니다. 플랜 업그레이드를 고려해보세요.
          </p>
        </div>
      )}
    </div>
  );
};

export default QuotaGauge;
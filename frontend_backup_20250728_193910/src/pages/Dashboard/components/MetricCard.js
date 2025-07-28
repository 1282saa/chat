import React from 'react';
import { ArrowUpIcon, ArrowDownIcon } from '@heroicons/react/24/solid';

const MetricCard = ({ title, value, icon: Icon, trend, color = 'blue' }) => {
  const isPositive = trend && trend.startsWith('+');
  const isNegative = trend && trend.startsWith('-');

  const colorStyles = {
    blue: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400',
    green: 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400',
    purple: 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400',
    orange: 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm hover:shadow-md transition-shadow duration-200 p-6">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-600 dark:text-gray-400">{title}</p>
          <p className="mt-2 text-3xl font-bold text-gray-900 dark:text-white">{value}</p>
          {trend && (
            <div className="mt-2 flex items-center text-sm">
              {isPositive && (
                <>
                  <ArrowUpIcon className="h-4 w-4 text-green-500 mr-1" />
                  <span className="text-green-600 dark:text-green-400 font-medium">{trend}</span>
                </>
              )}
              {isNegative && (
                <>
                  <ArrowDownIcon className="h-4 w-4 text-red-500 mr-1" />
                  <span className="text-red-600 dark:text-red-400 font-medium">{trend}</span>
                </>
              )}
              <span className="text-gray-500 dark:text-gray-400 ml-2">vs 어제</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorStyles[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
      </div>
    </div>
  );
};

export default MetricCard;
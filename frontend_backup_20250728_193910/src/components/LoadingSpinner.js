import React from "react";

const LoadingSpinner = ({ message = "로딩 중..." }) => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-dark-primary flex items-center justify-center transition-colors duration-300">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
        <p className="text-gray-600 dark:text-gray-300">{message}</p>
      </div>
    </div>
  );
};

export default LoadingSpinner;

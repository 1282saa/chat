import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ChatBubbleLeftRightIcon, ChartBarIcon } from '@heroicons/react/24/outline';

const MainNavToggle = () => {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const isDashboard = pathname.startsWith('/dashboard');
  const label = isDashboard ? '채팅' : '대시보드';
  const to = isDashboard ? '/chat' : '/dashboard';
  const Icon = isDashboard ? ChatBubbleLeftRightIcon : ChartBarIcon;

  const handleClick = (e) => {
    e.preventDefault();
    window.scrollTo(0, 0);
    navigate(to);
  };

  return (
    <button
      onClick={handleClick}
      className="flex items-center space-x-2 px-5 py-3 rounded-lg text-sm font-semibold transition-all duration-200 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-blue-600 dark:hover:text-blue-400"
    >
      <Icon className="h-5 w-5" />
      <span>{label}</span>
    </button>
  );
};

export default MainNavToggle;
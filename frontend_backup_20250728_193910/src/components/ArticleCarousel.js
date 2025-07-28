import React, { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';

const ArticleCarousel = ({ articles = [], onArticleClick }) => {
  const scrollContainerRef = useRef(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(true);

  // 디버깅용 로그
  console.log('🔍 ArticleCarousel - 받은 articles:', articles);
  console.log('🔍 ArticleCarousel - articles.length:', articles.length);

  // 스크롤 상태 업데이트
  const updateScrollButtons = () => {
    if (scrollContainerRef.current) {
      const { scrollLeft, scrollWidth, clientWidth } = scrollContainerRef.current;
      setCanScrollLeft(scrollLeft > 0);
      setCanScrollRight(scrollLeft < scrollWidth - clientWidth - 1);
    }
  };

  // 좌우 스크롤 함수
  const scroll = (direction) => {
    if (scrollContainerRef.current) {
      const scrollAmount = 296; // 카드 너비(280px) + 여백(16px)
      const newScrollLeft = direction === 'left' 
        ? scrollContainerRef.current.scrollLeft - scrollAmount
        : scrollContainerRef.current.scrollLeft + scrollAmount;
      
      scrollContainerRef.current.scrollTo({
        left: newScrollLeft,
        behavior: 'smooth'
      });
    }
  };

  // 카드 클릭 핸들러
  const handleCardClick = (article, index) => {
    if (onArticleClick) {
      onArticleClick(article, index);
    }
  };

  if (!articles || articles.length === 0) {
    return null;
  }

  return (
    <div className="w-full">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          📰 참고 기사 ({articles.length}개)
        </h3>
        
        {/* 스크롤 버튼 - 5개 이상일 때만 표시 */}
        {articles.length > 4 && (
          <div className="flex gap-2">
            <button
              onClick={() => scroll('left')}
              disabled={!canScrollLeft}
              className={`p-2 rounded-full transition-colors ${
                canScrollLeft
                  ? 'bg-gray-100 hover:bg-gray-200 text-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300'
                  : 'bg-gray-50 text-gray-300 dark:bg-gray-800 dark:text-gray-600 cursor-not-allowed'
              }`}
            >
              <ChevronLeftIcon className="h-4 w-4" />
            </button>
            <button
              onClick={() => scroll('right')}
              disabled={!canScrollRight}
              className={`p-2 rounded-full transition-colors ${
                canScrollRight
                  ? 'bg-gray-100 hover:bg-gray-200 text-gray-700 dark:bg-gray-700 dark:hover:bg-gray-600 dark:text-gray-300'
                  : 'bg-gray-50 text-gray-300 dark:bg-gray-800 dark:text-gray-600 cursor-not-allowed'
              }`}
            >
              <ChevronRightIcon className="h-4 w-4" />
            </button>
          </div>
        )}
      </div>

      {/* 캐러셀 컨테이너 */}
      <div className="relative">
        <div
          ref={scrollContainerRef}
          className="flex gap-4 overflow-x-auto scrollbar-hide pb-2"
          style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
          onScroll={updateScrollButtons}
        >
          {articles.map((article, index) => (
            <ArticleCard
              key={index}
              article={article}
              index={index + 1}
              onClick={() => handleCardClick(article, index)}
            />
          ))}
        </div>
      </div>
    </div>
  );
};

// 개별 기사 카드 컴포넌트
const ArticleCard = ({ article, index, onClick }) => {
  console.log('🔍 ArticleCard - 렌더링:', { article, index });
  
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2 }}
      className="flex-shrink-0 w-[280px] h-[140px] bg-[#F4F5FD] dark:bg-[#2A2A30] rounded-2xl cursor-pointer relative group overflow-hidden"
      onClick={onClick}
    >
      {/* 카드 내용을 flex로 구성 - 번호와 텍스트 영역 분리 */}
      <div className="flex h-full p-4">
        {/* 왼쪽: 번호 배지 영역 */}
        <div className="flex-shrink-0 w-8 h-8 mr-3 mt-1">
          <div className="w-6 h-6 bg-[#ECE8FF] dark:bg-[#3A3A40] rounded-full flex items-center justify-center">
            <span className="text-[#6A4BFF] dark:text-[#8B7BFF] text-xs font-bold">
              {index}
            </span>
          </div>
        </div>

        {/* 오른쪽: 제목과 날짜 영역 */}
        <div className="flex-1 flex flex-col justify-between min-w-0">
          {/* 제목 */}
          <h4 
            className="text-sm font-bold text-gray-900 dark:text-white leading-tight"
            style={{
              display: '-webkit-box',
              WebkitLineClamp: 4,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              wordBreak: 'keep-all',
              lineHeight: '1.3'
            }}
          >
            {article.title}
          </h4>

          {/* 날짜 - 하단 고정 */}
          <p className="text-xs text-[#8C8C8C] dark:text-gray-400 mt-2 flex-shrink-0">
            {article.date}
          </p>
        </div>
      </div>

      {/* 호버 효과 */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent to-white dark:to-gray-700 opacity-0 group-hover:opacity-10 rounded-2xl transition-opacity duration-200" />
    </motion.div>
  );
};

export default ArticleCarousel;
import React, { useState, useRef, useEffect } from 'react';
import { InformationCircleIcon } from '@heroicons/react/24/outline';

const CitationLink = ({ citationNumber, article, onPreview }) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const [tooltipPosition, setTooltipPosition] = useState({ top: 0, left: 0 });
  const linkRef = useRef(null);
  const tooltipRef = useRef(null);

  const handleMouseEnter = () => {
    if (linkRef.current) {
      const rect = linkRef.current.getBoundingClientRect();
      setTooltipPosition({
        top: rect.bottom + window.scrollY + 5,
        left: rect.left + window.scrollX
      });
      setShowTooltip(true);
    }
  };

  const handleMouseLeave = () => {
    setShowTooltip(false);
  };

  const handleClick = (e) => {
    e.preventDefault();
    
    // 기사 URL이 있으면 새 창에서 바로 열기
    if (article?.url) {
      window.open(article.url, '_blank', 'noopener,noreferrer');
    } else if (onPreview && article) {
      // URL이 없으면 미리보기 모달 열기
      onPreview(article);
    }
  };

  // 툴팁이 화면 밖으로 나가지 않도록 조정
  useEffect(() => {
    if (showTooltip && tooltipRef.current) {
      const tooltip = tooltipRef.current;
      const rect = tooltip.getBoundingClientRect();
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;

      let { top, left } = tooltipPosition;

      // 오른쪽 경계 체크
      if (rect.right > viewportWidth - 10) {
        left = viewportWidth - rect.width - 10;
      }

      // 왼쪽 경계 체크
      if (left < 10) {
        left = 10;
      }

      // 아래쪽 경계 체크
      if (rect.bottom > viewportHeight - 10) {
        top = tooltipPosition.top - rect.height - 10;
      }

      if (left !== tooltipPosition.left || top !== tooltipPosition.top) {
        setTooltipPosition({ top, left });
      }
    }
  }, [showTooltip, tooltipPosition]);

  return (
    <>
      <a
        ref={linkRef}
        href={article?.url || '#'}
        target={article?.url ? '_blank' : undefined}
        rel={article?.url ? 'noopener noreferrer' : undefined}
        className="inline-flex items-center cursor-pointer group no-underline"
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
        title={`출처 [${citationNumber}]: ${article?.title || '서울경제신문 기사'}`}
      >
        <sup className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 font-medium transition-colors underline decoration-dotted ml-0.5 hover:bg-blue-50 dark:hover:bg-blue-900/20 px-1 rounded">
          [{citationNumber}]
        </sup>
      </a>

      {/* 툴팁 */}
      {showTooltip && article && (
        <div
          ref={tooltipRef}
          className="fixed z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg p-3 max-w-sm"
          style={{
            top: `${tooltipPosition.top}px`,
            left: `${tooltipPosition.left}px`,
          }}
        >
          <div className="space-y-2">
            {/* 출처 번호 */}
            <div className="flex items-center space-x-2">
              <div className="bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 px-2 py-1 rounded text-xs font-medium">
                출처 [{citationNumber}]
              </div>
              <InformationCircleIcon className="h-4 w-4 text-gray-400" />
            </div>

            {/* 제목 */}
            <h4 className="font-medium text-gray-900 dark:text-white text-sm leading-tight">
              {article.title}
            </h4>

            {/* 메타 정보 */}
            <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
              {article.date && (
                <div>발행일: {article.date}</div>
              )}
              <div className="text-blue-600 dark:text-blue-400 font-medium">서울경제신문</div>
            </div>

            {/* 간단한 내용 미리보기 - 제거됨 (본문 노출 방지) */}

            {/* 액션 힌트 */}
            <div className="text-xs text-gray-400 dark:text-gray-500 pt-1 border-t border-gray-100 dark:border-gray-700 flex items-center gap-1">
              {article.url ? (
                <>
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-2M7 7l10 10M17 7v4" />
                  </svg>
                  <span>클릭하여 새 창에서 원문 보기</span>
                </>
              ) : (
                <span>클릭하여 자세히 보기</span>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default CitationLink;
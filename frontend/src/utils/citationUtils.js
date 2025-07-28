import React from 'react';
import CitationLink from '../components/CitationLink';
import ArticleCarousel from '../components/ArticleCarousel';

/**
 * 텍스트 내의 각주 패턴을 찾아서 CitationLink 컴포넌트로 변환
 * @param {string} text - 처리할 텍스트
 * @param {Array} sources - 출처 정보 배열
 * @param {Function} onPreview - 미리보기 핸들러
 * @returns {Array} React 엘리먼트 배열
 */
export const parseCitations = (text, sources = [], onPreview) => {
  if (!text || typeof text !== 'string') {
    return [text];
  }

  // 각주 패턴: [1], [2], [3] 등
  const citationPattern = /\[(\d+)\]/g;
  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = citationPattern.exec(text)) !== null) {
    const [fullMatch, citationNumber] = match;
    const citationNum = parseInt(citationNumber, 10);
    
    // 각주 앞의 텍스트 추가
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    
    // 해당하는 출처 찾기
    const source = sources.find(s => s.id === citationNum);
    
    // CitationLink 컴포넌트 추가
    parts.push(
      <CitationLink
        key={`citation-${citationNum}-${match.index}`}
        citationNumber={citationNum}
        article={source}
        onPreview={onPreview}
      />
    );
    
    lastIndex = match.index + fullMatch.length;
  }
  
  // 마지막 부분 추가
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  
  return parts.length > 0 ? parts : [text];
};

/**
 * 출처 목록을 캐러셀 형태로 렌더링하는 함수
 * @param {Array} sources - 출처 정보 배열
 * @returns {JSX.Element} 출처 목록 컴포넌트
 */
export const renderSourcesList = (sources = []) => {
  console.log('🔍 renderSourcesList - 받은 sources:', sources);
  console.log('🔍 renderSourcesList - sources.length:', sources.length);
  
  if (!sources || sources.length === 0) {
    console.log('🔍 renderSourcesList - sources가 비어있어서 null 반환');
    return null;
  }

  // sources 배열을 ArticleCarousel에서 기대하는 형태로 변환 (content 제외)
  const articlesForCarousel = sources.map(source => ({
    title: source.title || '제목 없음',
    date: source.date || '',
    url: source.url || '',
    // content 제거 - 본문 노출 방지
    originalSource: source // 원본 데이터 유지
  }));
  
  console.log('🔍 renderSourcesList - 변환된 articlesForCarousel:', articlesForCarousel);

  // 기사 클릭 핸들러 - 각주 시스템에서는 바로 외부 링크로 이동
  const handleArticleClick = (article, index) => {
    const originalSource = article.originalSource;
    
    if (originalSource.url) {
      window.open(originalSource.url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <div className="mt-6 pt-4 border-t border-gray-200 dark:border-gray-700">
      <ArticleCarousel 
        articles={articlesForCarousel}
        onArticleClick={handleArticleClick}
      />
    </div>
  );
};

/**
 * 메시지 내용에서 각주 스타일링을 위한 전처리
 * @param {string} content - 메시지 내용
 * @returns {string} 전처리된 내용
 */
export const preprocessMessageContent = (content) => {
  if (!content || typeof content !== 'string') {
    return content;
  }

  // 각주 패턴을 더 눈에 띄게 만들기 위한 전처리
  // 예: "내용[1]" -> "내용 [1]" (공백 추가)
  return content.replace(/([^[\s])\[(\d+)\]/g, '$1 [$2]');
};
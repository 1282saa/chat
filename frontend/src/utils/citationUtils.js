import CitationLink from "../components/news/CitationLink";
import ArticleCarousel from "../components/news/ArticleCarousel";

/**
 * 메시지 내용에서 인용 구문을 파싱합니다.
 * @param {string} content - 파싱할 메시지 내용
 * @returns {Array} 인용 정보 배열
 */
export const parseCitations = (content) => {
  if (!content) return [];
  
  const citationPattern = /\[(\d+)\]/g;
  const citations = [];
  let match;
  
  while ((match = citationPattern.exec(content)) !== null) {
    citations.push({
      number: parseInt(match[1], 10),
      position: match.index
    });
  }
  
  return citations;
};

/**
 * 소스 목록을 렌더링합니다.
 * @param {Array} sources - 소스 배열
 * @returns {JSX.Element} 렌더링된 소스 목록
 */
export const renderSourcesList = (sources) => {
  if (!sources || sources.length === 0) return null;
  
  return (
    <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
        참고 자료:
      </h4>
      <ul className="space-y-1">
        {sources.map((source, index) => (
          <li key={index} className="text-xs text-gray-600 dark:text-gray-400">
            [{index + 1}] {source.title || source.url}
          </li>
        ))}
      </ul>
    </div>
  );
};

/**
 * 메시지 내용을 전처리합니다.
 * @param {string} content - 전처리할 메시지 내용
 * @returns {string} 전처리된 메시지 내용
 */
export const preprocessMessageContent = (content) => {
  if (!content) return '';
  
  // 인용 구문을 링크로 변환하는 등의 전처리 작업
  return content.replace(/\[(\d+)\]/g, (match, number) => {
    return `[${number}]`;
  });
};
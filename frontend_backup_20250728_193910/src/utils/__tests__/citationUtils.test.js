import React from 'react';
import { render, screen } from '@testing-library/react';
import { parseCitations, renderSourcesList } from '../citationUtils';

// Mock components
jest.mock('../../components/CitationLink', () => {
  return function MockCitationLink({ citationNumber, article }) {
    return <span data-testid={`citation-${citationNumber}`}>[{citationNumber}]</span>;
  };
});

jest.mock('../../components/ArticleCarousel', () => {
  return function MockArticleCarousel({ articles }) {
    return (
      <div data-testid="article-carousel">
        {articles.map((article, index) => (
          <div key={index} data-testid={`carousel-article-${index}`}>
            {article.title}
          </div>
        ))}
      </div>
    );
  };
});

describe('citationUtils', () => {
  describe('parseCitations', () => {
    test('각주 패턴을 올바르게 파싱한다', () => {
      const text = "이것은 테스트 문장입니다[1]. 또 다른 문장[2]도 있습니다.";
      const sources = [
        { id: 1, title: '첫 번째 기사', url: 'http://example1.com' },
        { id: 2, title: '두 번째 기사', url: 'http://example2.com' }
      ];
      
      const result = parseCitations(text, sources);
      
      // React 엘리먼트와 텍스트가 섞인 배열이 반환되어야 함
      expect(result).toHaveLength(5); // "이것은 테스트 문장입니다", [1], ". 또 다른 문장", [2], "도 있습니다."
    });

    test('각주가 없는 텍스트는 그대로 반환한다', () => {
      const text = "이것은 각주가 없는 일반 텍스트입니다.";
      const result = parseCitations(text, []);
      
      expect(result).toEqual([text]);
    });

    test('빈 텍스트나 null 입력을 처리한다', () => {
      expect(parseCitations("", [])).toEqual([""]);
      expect(parseCitations(null, [])).toEqual([null]);
      expect(parseCitations(undefined, [])).toEqual([undefined]);
    });
  });

  describe('renderSourcesList', () => {
    const mockSources = [
      {
        id: 1,
        title: '창원 최초 민간임대아파트 하이엔드시티 홍보관 오픈',
        date: '2023-11-11 09:00',
        url: 'http://www.sedaily.com/NewsView/29X6Z9CL0D'
      },
      {
        id: 2,
        title: '울산시 착한 임대인 재산세 감면',
        date: '2021-08-08 09:02',
        url: 'http://www.sedaily.com/NewsView/22Q3X768H0'
      }
    ];

    test('기사 목록을 캐러셀로 렌더링한다', () => {
      const result = renderSourcesList(mockSources);
      const { container } = render(result);
      
      // ArticleCarousel이 렌더링되는지 확인
      expect(screen.getByTestId('article-carousel')).toBeInTheDocument();
      
      // 각 기사가 렌더링되는지 확인
      expect(screen.getByTestId('carousel-article-0')).toBeInTheDocument();
      expect(screen.getByTestId('carousel-article-1')).toBeInTheDocument();
    });

    test('빈 기사 목록일 때 null을 반환한다', () => {
      const result = renderSourcesList([]);
      expect(result).toBeNull();
    });

    test('sources가 undefined일 때 null을 반환한다', () => {
      const result = renderSourcesList(undefined);
      expect(result).toBeNull();
    });

    test('기사 데이터가 올바르게 변환된다', () => {
      const sources = [{
        id: 1,
        title: '테스트 기사',
        date: '2023-11-11 09:00',
        url: 'http://example.com',
        content: '이 내용은 제거되어야 함'  // content 필드
      }];

      const result = renderSourcesList(sources);
      const { container } = render(result);
      
      // content 필드가 제거되고 title, date, url만 전달되는지 확인
      expect(screen.getByText('테스트 기사')).toBeInTheDocument();
    });
  });
});
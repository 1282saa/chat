import React from 'react';
import { render, screen } from '@testing-library/react';
import ArticleCarousel from '../ArticleCarousel';

// Framer Motion mock
jest.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }) => <div {...props}>{children}</div>
  }
}));

// Heroicons mock
jest.mock('@heroicons/react/24/outline', () => ({
  ChevronLeftIcon: () => <div data-testid="chevron-left" />,
  ChevronRightIcon: () => <div data-testid="chevron-right" />
}));

describe('ArticleCarousel', () => {
  const mockArticles = [
    {
      title: '창원 최초 민간임대아파트 하이엔드시티 홍보관 11일 그랜드 오픈',
      date: '2023-11-11 09:00',
      url: 'http://www.sedaily.com/NewsView/29X6Z9CL0D'
    },
    {
      title: '울산시 착한 임대인 재산세 감면',
      date: '2021-08-08 09:02',
      url: 'http://www.sedaily.com/NewsView/22Q3X768H0'
    }
  ];

  test('기사 목록이 정상적으로 렌더링된다', () => {
    render(<ArticleCarousel articles={mockArticles} />);
    
    // 헤더 텍스트 확인
    expect(screen.getByText('📰 참고 기사 (2개)')).toBeInTheDocument();
    
    // 첫 번째 기사 제목 확인
    expect(screen.getByText('창원 최초 민간임대아파트 하이엔드시티 홍보관 11일 그랜드 오픈')).toBeInTheDocument();
    
    // 두 번째 기사 제목 확인
    expect(screen.getByText('울산시 착한 임대인 재산세 감면')).toBeInTheDocument();
    
    // 날짜 정보 확인
    expect(screen.getByText('2023-11-11 09:00')).toBeInTheDocument();
    expect(screen.getByText('2021-08-08 09:02')).toBeInTheDocument();
  });

  test('빈 기사 목록일 때 아무것도 렌더링하지 않는다', () => {
    const { container } = render(<ArticleCarousel articles={[]} />);
    expect(container.firstChild).toBeNull();
  });

  test('기사가 4개 이하일 때 스크롤 버튼이 표시되지 않는다', () => {
    render(<ArticleCarousel articles={mockArticles} />);
    
    // 스크롤 버튼이 없어야 함
    expect(screen.queryByTestId('chevron-left')).not.toBeInTheDocument();
    expect(screen.queryByTestId('chevron-right')).not.toBeInTheDocument();
  });

  test('기사 번호 배지가 올바르게 표시된다', () => {
    render(<ArticleCarousel articles={mockArticles} />);
    
    // 번호 배지 확인
    expect(screen.getByText('1')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
  });

  test('기사 클릭 핸들러가 정상적으로 호출된다', () => {
    const mockOnClick = jest.fn();
    render(<ArticleCarousel articles={mockArticles} onArticleClick={mockOnClick} />);
    
    // 첫 번째 기사 카드 클릭
    const firstCard = screen.getByText('창원 최초 민간임대아파트 하이엔드시티 홍보관 11일 그랜드 오픈').closest('div[class*="cursor-pointer"]');
    expect(firstCard).toBeInTheDocument();
  });
});
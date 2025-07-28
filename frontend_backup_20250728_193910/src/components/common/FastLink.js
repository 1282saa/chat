import React from 'react';
import { Link } from 'react-router-dom';
import { useLinkPrefetch } from '../../hooks/usePrefetch';

/**
 * 프리페칭 기능이 포함된 빠른 링크 컴포넌트
 */
const FastLink = ({ 
  to, 
  children, 
  className = '', 
  onMouseEnter,
  ...props 
}) => {
  const { prefetchRoute } = useLinkPrefetch();

  const handleMouseEnter = (e) => {
    // 기존 onMouseEnter 이벤트 실행
    if (onMouseEnter) {
      onMouseEnter(e);
    }
    
    // 경로 프리페칭
    prefetchRoute(to);
  };

  return (
    <Link
      to={to}
      className={className}
      onMouseEnter={handleMouseEnter}
      {...props}
    >
      {children}
    </Link>
  );
};

export default FastLink;
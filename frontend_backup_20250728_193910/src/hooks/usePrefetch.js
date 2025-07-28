import { useCallback } from 'react';

/**
 * 컴포넌트 프리로딩을 위한 커스텀 훅
 */
export const usePrefetch = () => {
  // 프로젝트 상세 페이지 프리로딩
  const prefetchProjectDetail = useCallback(() => {
    // ProjectDetail 컴포넌트를 미리 로드
    import('../components/ProjectDetail').then(() => {
      console.log('🚀 ProjectDetail 컴포넌트 프리로드 완료');
    }).catch((error) => {
      console.warn('⚠️ ProjectDetail 프리로드 실패:', error);
    });
  }, []);

  // 프로젝트 생성 페이지 프리로딩  
  const prefetchCreateProject = useCallback(() => {
    import('../components/CreateProject').then(() => {
      console.log('🚀 CreateProject 컴포넌트 프리로드 완료');
    }).catch((error) => {
      console.warn('⚠️ CreateProject 프리로드 실패:', error);
    });
  }, []);

  return {
    prefetchProjectDetail,
    prefetchCreateProject,
  };
};

/**
 * 링크 프리페칭을 위한 유틸리티
 */
export const useLinkPrefetch = () => {
  const prefetchRoute = useCallback((path) => {
    // 특정 경로에 해당하는 컴포넌트를 프리로드
    if (path.startsWith('/projects/') && path !== '/projects') {
      // 프로젝트 상세 페이지
      import('../components/ProjectDetail').catch(() => {});
    } else if (path === '/projects') {
      // 프로젝트 목록 페이지
      import('../components/ProjectList').catch(() => {});
    } else if (path === '/create') {
      // 프로젝트 생성 페이지
      import('../components/CreateProject').catch(() => {});
    }
  }, []);

  return { prefetchRoute };
};
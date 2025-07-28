/**
 * 무한 렌더링 디버깅을 위한 유틸리티 함수들
 */
import React from "react";

// 렌더링 횟수를 추적하는 맵
const renderCounts = new Map();

/**
 * 컴포넌트 렌더링 횟수를 추적하는 함수
 * @param {string} componentName - 컴포넌트 이름
 * @param {object} props - 컴포넌트 props (선택적)
 */
export const trackRender = (componentName, props = {}) => {
  // 운영 환경에서도 심각한 렌더링 문제는 추적
  if (process.env.NODE_ENV === "production") {
    // 운영 환경에서는 경고 레벨만 표시
    const count = renderCounts.get(componentName) || 0;
    const newCount = count + 1;
    renderCounts.set(componentName, newCount);

    if (newCount > 20) {
      console.warn(
        `🚨 [PRODUCTION WARNING] ${componentName} 컴포넌트가 ${newCount}번 렌더링되었습니다!`
      );
    }
    return newCount;
  }

  const count = renderCounts.get(componentName) || 0;
  const newCount = count + 1;
  renderCounts.set(componentName, newCount);

  // 10회 이상 렌더링되면 경고
  if (newCount > 10) {
    console.warn(
      `🚨 [RENDER WARNING] ${componentName} 컴포넌트가 ${newCount}번 렌더링되었습니다!`,
      props
    );
  } else if (newCount > 5) {
    console.log(`⚠️ [RENDER] ${componentName} 렌더링 #{${newCount}}`, props);
  } else {
    console.log(`🔄 [RENDER] ${componentName} 렌더링 #{${newCount}}`);
  }

  return newCount;
};

/**
 * 렌더링 통계를 초기화하는 함수
 */
export const resetRenderStats = () => {
  renderCounts.clear();
  console.log("🔄 렌더링 통계가 초기화되었습니다.");
};

/**
 * 현재 렌더링 통계를 출력하는 함수
 */
export const printRenderStats = () => {
  if (renderCounts.size === 0) {
    console.log("📊 렌더링 통계: 추적된 컴포넌트가 없습니다.");
    return;
  }

  console.group("📊 렌더링 통계");
  renderCounts.forEach((count, componentName) => {
    const status = count > 10 ? "🚨" : count > 5 ? "⚠️" : "✅";
    console.log(`${status} ${componentName}: ${count}회`);
  });
  console.groupEnd();
};

/**
 * useEffect 의존성 변화를 추적하는 훅
 * @param {Array} deps - 의존성 배열
 * @param {string} name - 추적할 이름
 */
export const useDepsTracker = (deps, name) => {
  const prevDeps = React.useRef();

  React.useEffect(() => {
    // 개발 모드가 아니면 추적하지 않음
    if (process.env.NODE_ENV !== "development") return;
    if (prevDeps.current) {
      const changedDeps = deps
        .map((dep, i) => ({
          index: i,
          prev: prevDeps.current[i],
          current: dep,
          changed: prevDeps.current[i] !== dep,
        }))
        .filter((dep) => dep.changed);

      if (changedDeps.length > 0) {
        console.log(`🔄 [DEPS CHANGED] ${name}:`, changedDeps);
      }
    }
    prevDeps.current = deps;
  });
};

// 전역에서 렌더링 통계에 접근할 수 있도록 설정
if (typeof window !== "undefined") {
  window.debugRender = {
    printStats: printRenderStats,
    resetStats: resetRenderStats,
    trackRender,
  };

  // 채팅 디버깅 도구 추가
  window.chatDebug = {
    enableSendMessage: () => {
      console.log("🔧 [DEBUG] canSendMessage 강제 활성화");
      // useChat 훅에서 setCanSendMessage에 접근하기 위한 전역 함수
      if (window.setCanSendMessageGlobal) {
        window.setCanSendMessageGlobal(true);
        console.log("✅ 메시지 전송이 활성화되었습니다!");
      } else {
        console.log("❌ setCanSendMessage 함수를 찾을 수 없습니다.");
      }
    },
  };

  if (process.env.NODE_ENV === "development") {
    console.log(
      "🔧 개발 모드: window.debugRender로 렌더링 디버깅 도구에 접근할 수 있습니다."
    );
    console.log("   - window.debugRender.printStats(): 렌더링 통계 출력");
    console.log("   - window.debugRender.resetStats(): 통계 초기화");
    console.log(
      "   - window.chatDebug.enableSendMessage(): 메시지 전송 강제 활성화"
    );
  } else {
    console.log("🛡️ 운영 모드: 렌더링 모니터링이 활성화되었습니다.");
  }
}

import React from "react";

// Shimmer 애니메이션을 위한 CSS 클래스
const shimmerEffect =
  "relative overflow-hidden before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_1.5s_infinite] before:bg-gradient-to-r before:from-transparent before:via-white/20 before:to-transparent";

// 기본 스켈레톤 박스 - Soft-Glass 스타일
export const SkeletonBox = ({
  width = "w-full",
  height = "h-4",
  className = "",
}) => (
  <div
    className={`bg-gray-200/80 dark:bg-gray-600/60 rounded-lg animate-pulse backdrop-blur-sm border border-gray-300/40 dark:border-gray-500/40 ${shimmerEffect} ${width} ${height} ${className}`}
  ></div>
);

// 원형 스켈레톤 (아바타용) - Soft-Glass 스타일
export const SkeletonCircle = ({ size = "w-10 h-10", className = "" }) => (
  <div
    className={`bg-gray-200/80 dark:bg-gray-600/60 rounded-full animate-pulse backdrop-blur-sm border border-gray-300/40 dark:border-gray-500/40 ${shimmerEffect} ${size} ${className}`}
  ></div>
);

// 채팅 메시지 스켈레톤 - 개선된 스타일
export const ChatMessageSkeleton = ({ isUser = false }) => (
  <div className={`group relative ${isUser ? "ml-8" : "mr-8"} mb-6`}>
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      {isUser ? (
        // 사용자 메시지 스켈레톤 - 블루 톤
        <div className="max-w-[85%] rounded-xl px-6 py-4 bg-blue-100/80 dark:bg-blue-900/30 animate-pulse backdrop-blur-sm border border-blue-200/60 dark:border-blue-700/50">
          <div className="space-y-2">
            <SkeletonBox
              width="w-3/4"
              height="h-4"
              className="bg-blue-200/60 dark:bg-blue-800/40"
            />
            <SkeletonBox
              width="w-full"
              height="h-4"
              className="bg-blue-200/60 dark:bg-blue-800/40"
            />
            <SkeletonBox
              width="w-1/2"
              height="h-4"
              className="bg-blue-200/60 dark:bg-blue-800/40"
            />
          </div>
          <SkeletonBox
            width="w-16"
            height="h-3"
            className="mt-3 bg-blue-200/40 dark:bg-blue-800/30"
          />
        </div>
      ) : (
        // AI 메시지 스켈레톤 - Soft-Glass 스타일
        <div className="max-w-[85%] w-full backdrop-blur-sm bg-white/70 dark:bg-gray-800/60 rounded-xl p-4 border border-white/40 dark:border-gray-700/50">
          <div className="space-y-3">
            <SkeletonBox width="w-full" height="h-4" />
            <SkeletonBox width="w-5/6" height="h-4" />
            <SkeletonBox width="w-4/5" height="h-4" />
            <SkeletonBox width="w-3/4" height="h-4" />
            <SkeletonBox width="w-2/3" height="h-4" />
          </div>

          {/* 복사 버튼 영역 스켈레톤 */}
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <SkeletonBox width="w-20" height="h-8" className="rounded-xl" />
              <SkeletonBox width="w-16" height="h-6" className="rounded-lg" />
            </div>
            <SkeletonBox width="w-12" height="h-3" />
          </div>
        </div>
      )}
    </div>
  </div>
);

// 프로젝트 카드 스켈레톤
export const ProjectCardSkeleton = () => (
  <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 h-[280px] flex flex-col animate-pulse">
    <div className="p-6 flex flex-col flex-1">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center space-x-3 flex-1">
          <SkeletonCircle size="w-12 h-12" />
          <div className="flex-1 space-y-2">
            <SkeletonBox width="w-3/4" height="h-5" />
            <SkeletonBox width="w-1/2" height="h-4" />
          </div>
        </div>
        <SkeletonBox width="w-6" height="h-6" className="rounded" />
      </div>

      <div className="flex-1 space-y-3 mb-4">
        <SkeletonBox width="w-full" height="h-4" />
        <SkeletonBox width="w-5/6" height="h-4" />
        <SkeletonBox width="w-4/5" height="h-4" />
      </div>

      <div className="flex items-center justify-between text-sm">
        <SkeletonBox width="w-20" height="h-4" />
        <SkeletonBox width="w-16" height="h-4" />
      </div>
    </div>
  </div>
);

// 프로젝트 목록 스켈레톤
export const ProjectListSkeleton = ({ count = 6 }) => (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    {Array.from({ length: count }, (_, index) => (
      <ProjectCardSkeleton key={index} />
    ))}
  </div>
);

// 채팅 인터페이스 스켈레톤
export const ChatInterfaceSkeleton = () => (
  <div className="h-full flex flex-col bg-white dark:bg-gray-900 animate-pulse">
    {/* 헤더 스켈레톤 */}
    <div className="border-b border-gray-200 dark:border-gray-700 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <SkeletonBox width="w-16" height="h-8" className="rounded-lg" />
          <SkeletonBox width="w-32" height="h-6" />
        </div>
        <div className="flex items-center space-x-2">
          <SkeletonBox width="w-20" height="h-6" className="rounded-full" />
        </div>
      </div>
    </div>

    {/* 메시지 영역 스켈레톤 */}
    <div className="flex-1 overflow-y-auto p-4 space-y-6">
      <ChatMessageSkeleton isUser={true} />
      <ChatMessageSkeleton isUser={false} />
      <ChatMessageSkeleton isUser={true} />
      <ChatMessageSkeleton isUser={false} />
    </div>

    {/* 입력 영역 스켈레톤 */}
    <div className="border-t border-gray-200 dark:border-gray-700 p-4">
      <div className="flex space-x-3">
        <SkeletonBox width="flex-1" height="h-12" className="rounded-lg" />
        <SkeletonBox width="w-12" height="h-12" className="rounded-lg" />
      </div>
    </div>
  </div>
);

// 페이지 스켈레톤 (이미 있던 것을 향상)
export const PageSkeleton = () => (
  <div className="min-h-screen bg-gray-50 dark:bg-dark-primary">
    <div className="bg-white dark:bg-dark-secondary border-b border-gray-200 dark:border-gray-700 animate-pulse">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <SkeletonBox width="w-32" height="h-6" />
      </div>
    </div>
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="space-y-6">
        <SkeletonBox width="w-48" height="h-8" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }, (_, index) => (
            <div
              key={index}
              className="bg-white dark:bg-dark-secondary rounded-xl border border-gray-200 dark:border-gray-700 p-6 animate-pulse"
            >
              <div className="space-y-4">
                <SkeletonBox width="w-3/4" height="h-5" />
                <SkeletonBox width="w-full" height="h-4" />
                <SkeletonBox width="w-5/6" height="h-4" />
                <div className="flex justify-between mt-4">
                  <SkeletonBox width="w-16" height="h-4" />
                  <SkeletonBox width="w-12" height="h-4" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

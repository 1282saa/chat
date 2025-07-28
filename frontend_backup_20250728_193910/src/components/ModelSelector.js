import React, { useState } from "react";
import { ChevronDownIcon, SparklesIcon } from "@heroicons/react/24/outline";

// 실제 사용되는 APAC Claude 모델들 (서울 리전 테스트 완료)
const MODELS = [
  {
    id: "apac.anthropic.claude-3-haiku-20240307-v1:0",
    name: "Claude 3 Haiku (APAC)",
    provider: "Anthropic",
    category: "fast",
    speed: "초고속 (1.89초)",
    quality: "좋음",
    description: "빠른 응답이 필요한 간단한 질문에 최적화",
    recommended: true,
    tier: "fast",
  },
  {
    id: "apac.anthropic.claude-3-sonnet-20240229-v1:0",
    name: "Claude 3 Sonnet (APAC)",
    provider: "Anthropic",
    category: "balanced",
    speed: "빠름 (3.22초)",
    quality: "우수",
    description: "균형잡힌 성능과 속도, 일반적인 질문에 적합",
    recommended: true,
    tier: "balanced",
  },
  {
    id: "apac.anthropic.claude-3-5-sonnet-20240620-v1:0",
    name: "Claude 3.5 Sonnet (APAC)",
    provider: "Anthropic",
    category: "high_performance",
    speed: "빠름 (3.92초)",
    quality: "고품질",
    description: "고품질 답변과 창의적 작업에 최적화",
    recommended: true,
    tier: "high_performance",
  },
  {
    id: "apac.anthropic.claude-3-7-sonnet-20250219-v1:0",
    name: "Claude 3.7 Sonnet (APAC)",
    provider: "Anthropic",
    category: "advanced",
    speed: "보통 (4.17초)",
    quality: "고품질",
    description: "2025년 최신 기술, 복잡한 분석에 최적화",
    new: true,
    tier: "advanced",
  },
  {
    id: "apac.anthropic.claude-sonnet-4-20250514-v1:0",
    name: "Claude Sonnet 4 (APAC)",
    provider: "Anthropic",
    category: "premium",
    speed: "보통 (4.48초)",
    quality: "최고급",
    description: "최고급 품질, 전문적 분석 필요시 사용",
    tier: "premium",
  },
  {
    id: "apac.anthropic.claude-3-5-sonnet-20241022-v2:0",
    name: "Claude 3.5 Sonnet v2 (APAC)",
    provider: "Anthropic",
    category: "latest",
    speed: "느림 (5.78초)",
    quality: "최고급",
    description: "최신 기능과 향상된 추론, 복합 작업에 최적",
    new: true,
    tier: "latest",
  },
];

const ModelSelector = ({ selectedModel, onModelChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [filter, setFilter] = useState("all");

  console.log("🤖 ModelSelector 렌더링됨:", { selectedModel, isOpen });

  const currentModel =
    MODELS.find((model) => model.id === selectedModel) || MODELS[0];

  const filteredModels = MODELS.filter((model) => {
    if (filter === "all") return true;
    if (filter === "recommended") return model.recommended;
    if (filter === "new") return model.new;
    return model.category === filter;
  });

  const handleModelSelect = (modelId) => {
    onModelChange(modelId);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      {/* 모델 선택 버튼 - 컴팩트 버전 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-800 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 border border-gray-300 dark:border-gray-600 shadow-sm transition-all duration-200 text-xs"
        title={`${currentModel.name} (${currentModel.provider})`}
      >
        <SparklesIcon className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
        <span className="text-gray-700 dark:text-gray-300 font-medium">
          {currentModel.name.replace(/Claude |Llama |Nova /, "")}
        </span>
        <ChevronDownIcon
          className={`h-3 w-3 text-gray-500 transition-transform ${
            isOpen ? "rotate-180" : ""
          }`}
        />
      </button>

      {/* 드롭다운 메뉴 */}
      {isOpen && (
        <div className="absolute bottom-full left-0 mb-2 bg-white dark:bg-dark-secondary  rounded-lg shadow-lg z-50 max-h-[400px] overflow-hidden min-w-[300px]">
          {/* 필터 버튼들 */}
          <div className="p-3 ">
            <div className="flex gap-1 text-xs">
              {[
                { key: "all", label: "전체" },
                { key: "recommended", label: "추천" },
                { key: "fast", label: "빠름" },
                { key: "balanced", label: "균형" },
                { key: "premium", label: "프리미엄" },
                { key: "new", label: "최신" },
              ].map((filterOption) => (
                <button
                  key={filterOption.key}
                  onClick={() => setFilter(filterOption.key)}
                  className={`px-2 py-1 rounded transition-colors ${
                    filter === filterOption.key
                      ? "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                      : "text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-dark-tertiary"
                  }`}
                >
                  {filterOption.label}
                </button>
              ))}
            </div>
          </div>

          {/* 모델 목록 */}
          <div className="max-h-[300px] overflow-y-auto">
            {filteredModels.map((model) => (
              <button
                key={model.id}
                onClick={() => handleModelSelect(model.id)}
                className={`w-full p-3 text-left hover:bg-gray-50 dark:hover:bg-gray-700 last:border-b-0 transition-colors ${
                  model.id === selectedModel
                    ? "bg-blue-50 dark:bg-blue-900/20"
                    : ""
                }`}
              >
                <div className="flex-1 min-w-0">
                  <div className="mb-1">
                    <span className="font-medium text-gray-900 dark:text-white">
                      {model.name}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                    {model.provider} • 속도: {model.speed} • 품질:{" "}
                    {model.quality}
                  </div>
                  <div className="text-xs text-gray-600 dark:text-gray-400">
                    {model.description}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 배경 클릭 시 닫기 */}
      {isOpen && (
        <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
      )}
    </div>
  );
};

export default ModelSelector;

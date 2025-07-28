import React, { useState, useEffect } from "react";
import { toast } from "react-hot-toast";
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  XMarkIcon,
  SparklesIcon,
  HashtagIcon,
} from "@heroicons/react/24/outline";
import { promptCardAPI, handleAPIError } from "../services/api";
import ChatWindow from "./chat/ChatWindow";

const PromptCardManager = ({ projectId, projectName }) => {
  const [promptCards, setPromptCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editingCard, setEditingCard] = useState(null);
  const [showForm, setShowForm] = useState(false);

  useEffect(() => {
    loadPromptCards();
  }, [projectId]);

  const loadPromptCards = async () => {
    try {
      setLoading(true);
      const response = await promptCardAPI.getPromptCards(projectId, true);
      setPromptCards(response.promptCards || []);
    } catch (error) {
      console.error("프롬프트 카드 로드 실패:", error);
      const errorInfo = handleAPIError(error);
      toast.error(errorInfo.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveCard = async (cardData) => {
    try {
      // 백엔드에 맞는 형식으로 데이터 변환
      const backendData = {
        title: cardData.title,
        prompt_text: cardData.prompt_text,
        tags: cardData.tags || [],
        isActive: cardData.enabled !== false, // enabled를 isActive로 변환
      };

      if (editingCard) {
        // 수정
        await promptCardAPI.updatePromptCard(
          projectId,
          editingCard.promptId || editingCard.prompt_id,
          backendData
        );
        toast.success("프롬프트가 수정되었습니다");
      } else {
        // 새로 생성
        await promptCardAPI.createPromptCard(projectId, backendData);
        toast.success("프롬프트가 생성되었습니다");
      }

      setShowForm(false);
      setEditingCard(null);

      // 백엔드 저장 성공 후 전체 데이터 다시 로드 (페이지 새로고침 없이)
      await loadPromptCards();
    } catch (error) {
      console.error("프롬프트 저장 실패:", error);
      const errorInfo = handleAPIError(error);
      toast.error(errorInfo.message);
    }
  };

  const handleDeleteCard = async (promptId) => {
    if (!window.confirm("정말로 이 프롬프트를 삭제하시겠습니까?")) {
      return;
    }

    try {
      // 백엔드에서 삭제 먼저 실행
      await promptCardAPI.deletePromptCard(projectId, promptId);
      toast.success("프롬프트가 삭제되었습니다");

      // 삭제 성공 후 UI에서 제거
      setPromptCards((prev) =>
        prev.filter((card) => (card.promptId || card.prompt_id) !== promptId)
      );

      // 추가로 전체 데이터 다시 로드
      await loadPromptCards();
    } catch (error) {
      console.error("프롬프트 삭제 실패:", error);
      const errorInfo = handleAPIError(error);
      toast.error(errorInfo.message);
    }
  };

  const handleEditCard = async (card) => {
    console.log("프롬프트 수정 버튼 클릭:", card);

    // 프롬프트 텍스트 내용이 없으면 S3에서 가져오기
    let cardWithContent = { ...card };

    if (!card.prompt_text && !card.content) {
      try {
        console.log("S3에서 프롬프트 내용 로드 중...");
        const contentResponse = await promptCardAPI.getPromptContent(
          projectId,
          card.promptId || card.prompt_id
        );
        cardWithContent.prompt_text = contentResponse.content;
        console.log(
          "S3에서 프롬프트 내용 로드 완료:",
          contentResponse.content?.length,
          "문자"
        );
      } catch (error) {
        console.error("프롬프트 내용 로드 실패:", error);
        toast.error("프롬프트 내용을 불러올 수 없습니다");
        return;
      }
    }

    setEditingCard(cardWithContent);
    setShowForm(true);
  };

  const handleNewCard = () => {
    console.log("새 프롬프트 추가 버튼 클릭");
    setEditingCard(null);
    setShowForm(true);
  };

  const handleCancelForm = () => {
    console.log("모달 취소 버튼 클릭");
    setShowForm(false);
    setEditingCard(null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full bg-gray-50 dark:bg-dark-primary">
      {/* 채팅 인터페이스 */}
      <div className="flex-1 min-w-0 h-full overflow-hidden">
        <ChatWindow
          projectId={projectId}
          projectName={projectName}
          promptCards={promptCards}
          isAdminMode={true}
        />
      </div>

      {/* 프롬프트 관리 사이드바 (우측) */}
      <div className="w-80 h-full bg-white dark:bg-dark-primary flex flex-col shadow-lg border-l border-gray-200 dark:border-gray-700 flex-shrink-0">
        <div className="flex-shrink-0 p-4 bg-gray-50 dark:bg-dark-primary">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800 dark:text-white">
              프롬프트 카드
            </h2>
            <button
              onClick={handleNewCard}
              className="inline-flex items-center px-4 py-2 text-sm bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors shadow-md hover:shadow-lg font-medium"
            >
              <PlusIcon className="h-4 w-4 mr-1.5" />새 추가
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0 bg-gray-50 dark:bg-dark-secondary custom-scrollbar">
          {promptCards.length === 0 ? (
            <div className="text-center py-8">
              <SparklesIcon className="h-12 w-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                프롬프트 카드가 없습니다
              </p>
              <button
                onClick={handleNewCard}
                className="inline-flex items-center px-4 py-2 bg-blue-600 dark:bg-blue-500 text-white rounded-lg hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors shadow-sm font-medium"
              >
                <PlusIcon className="h-4 w-4 mr-1.5" />첫 번째 카드 만들기
              </button>
            </div>
          ) : (
            promptCards.map((card) => (
              <PromptCard
                key={card.promptId || card.prompt_id}
                card={card}
                onEdit={() => handleEditCard(card)}
                onDelete={() =>
                  handleDeleteCard(card.promptId || card.prompt_id)
                }
              />
            ))
          )}
        </div>
      </div>

      {/* 프롬프트 편집 폼 모달 */}
      {showForm && (
        <PromptFormModal
          isOpen={showForm}
          onSubmit={handleSaveCard}
          onCancel={handleCancelForm}
          initialData={editingCard}
        />
      )}
      
      {/* 스크롤바 스타일 */}
      <style jsx>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 8px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
          border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #d1d5db;
          border-radius: 4px;
          border: 1px solid #f3f4f6;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #9ca3af;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:active {
          background: #6b7280;
        }
        /* 다크모드 스크롤바 */
        .dark .custom-scrollbar::-webkit-scrollbar-thumb {
          background: #4b5563;
          border: 1px solid #374151;
        }
        .dark .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: #6b7280;
        }
        .dark .custom-scrollbar::-webkit-scrollbar-thumb:active {
          background: #9ca3af;
        }
      `}</style>
    </div>
  );
};

// 간단한 프롬프트 카드 컴포넌트
const PromptCard = ({ card, onEdit, onDelete }) => {
  return (
    <div className="bg-white dark:bg-gray-600 rounded-xl p-4 flex flex-col space-y-3 shadow-md dark:shadow-lg hover:shadow-lg dark:hover:shadow-xl transition-all duration-200 hover:bg-blue-50 dark:hover:bg-gray-500">
      {/* Header: Title and Actions */}
      <div className="flex items-start justify-between">
        <h3 className="font-semibold text-sm text-gray-800 dark:text-white leading-tight pr-2 flex-1">
          {card.title || `프롬프트 ${card.promptId || card.prompt_id}`}
        </h3>
        <div className="flex items-center flex-shrink-0">
          <button
            onClick={async (e) => {
              e.preventDefault();
              e.stopPropagation();
              await onEdit();
            }}
            className="p-1 text-gray-500 dark:text-gray-400 rounded-full hover:bg-gray-100 dark:hover:bg-dark-secondary hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
          >
            <PencilIcon className="h-4 w-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-1 text-gray-500 dark:text-gray-400 rounded-full hover:bg-gray-100 dark:hover:bg-dark-secondary hover:text-red-600 dark:hover:text-red-400 transition-colors"
          >
            <TrashIcon className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Tags */}
      {card.tags && card.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {card.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-dark-secondary text-gray-700 dark:text-gray-300 rounded-full"
            >
              #{tag}
            </span>
          ))}
          {card.tags.length > 3 && (
            <span className="text-xs text-gray-500 dark:text-gray-400">
              +{card.tags.length - 3}
            </span>
          )}
        </div>
      )}

      {/* Content Snippet */}
      {(card.content || card.prompt_text) && (
        <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed line-clamp-2">
          {card.content || card.prompt_text}
        </p>
      )}

      {/* Date */}
      <div className="flex items-end justify-between pt-2 text-xs text-gray-400 dark:text-gray-500">
        <span className="flex-shrink-0">
          생성:{" "}
          {new Date(card.createdAt || new Date()).toLocaleDateString("ko-KR", {
            year: "2-digit",
            month: "2-digit",
            day: "2-digit",
          })}
        </span>
        {card.updatedAt &&
          new Date(card.updatedAt) > new Date(card.createdAt) && (
            <span className="flex-shrink-0 ml-2">
              수정:{" "}
              {new Date(card.updatedAt).toLocaleDateString("ko-KR", {
                year: "2-digit",
                month: "2-digit",
                day: "2-digit",
              })}
            </span>
          )}
      </div>
    </div>
  );
};

// 간단한 프롬프트 편집 폼 모달
const PromptFormModal = ({ isOpen, onSubmit, onCancel, initialData }) => {
  const [formData, setFormData] = useState({
    title: "",
    prompt_text: "",
    tags: [],
    enabled: true,
  });
  const [tagInput, setTagInput] = useState("");

  useEffect(() => {
    if (initialData) {
      setFormData({
        title: initialData.title || "",
        prompt_text: initialData.prompt_text || initialData.content || "",
        tags: Array.isArray(initialData.tags) ? [...initialData.tags] : [],
        enabled:
          initialData.enabled !== false && initialData.isActive !== false, // isActive도 체크
      });
    }
  }, [initialData]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.prompt_text.trim()) {
      toast.error("프롬프트 내용을 입력해주세요");
      return;
    }
    onSubmit(formData);
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleTagAdd = (e) => {
    if (e.key === "Enter" && tagInput.trim()) {
      e.preventDefault();
      const newTag = tagInput.trim();
      if (!formData.tags.includes(newTag) && formData.tags.length < 5) {
        setFormData((prev) => ({
          ...prev,
          tags: [...prev.tags, newTag],
        }));
      }
      setTagInput("");
    }
  };

  const handleTagRemove = (tagToRemove) => {
    setFormData((prev) => ({
      ...prev,
      tags: prev.tags.filter((tag) => tag !== tagToRemove),
    }));
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-dark-secondary rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden shadow-xl dark:shadow-none transition-colors duration-300 ">
        {/* 헤더 */}
        <div className=" p-6 bg-white dark:bg-dark-secondary">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gray-100 dark:bg-dark-tertiary rounded-lg flex items-center justify-center">
                {initialData ? (
                  <PencilIcon className="h-6 w-6 text-gray-600 dark:text-gray-300" />
                ) : (
                  <PencilIcon className="h-6 w-6 text-gray-600 dark:text-gray-300" />
                )}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  {initialData ? "프롬프트 편집" : "새 프롬프트"}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {initialData
                    ? "프롬프트 내용을 수정하세요"
                    : "새로운 프롬프트를 작성하세요"}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onCancel}
              className="p-2 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-tertiary transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>

        <form
          onSubmit={handleSubmit}
          className="p-6 space-y-6 overflow-y-auto max-h-[calc(90vh-120px)]"
        >
          {/* 제목 필드 */}
          <div className="space-y-2">
            <label className="flex items-center text-sm font-semibold text-gray-800 dark:text-gray-200">
              프롬프트 제목
            </label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => handleChange("title", e.target.value)}
              className="w-full px-4 py-3  rounded-xl bg-gray-50 dark:bg-dark-tertiary text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-500/30 transition-all duration-200"
              placeholder="프롬프트 제목을 입력하세요"
            />
          </div>

          {/* 해시태그 */}
          <div className="space-y-2">
            <label className="flex items-center text-sm font-semibold text-gray-800 dark:text-gray-200">
              <HashtagIcon className="h-4 w-4 mr-2 text-gray-500 dark:text-gray-400" />
              태그
            </label>
            <div className="space-y-3">
              {/* 태그 입력 */}
              <input
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={handleTagAdd}
                className="w-full px-4 py-3  rounded-xl bg-gray-50 dark:bg-dark-tertiary text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 dark:focus:ring-blue-500/30 transition-all duration-200"
                placeholder="태그를 입력하고 Enter를 누르세요 (최대 5개)"
                maxLength={20}
                disabled={formData.tags.length >= 5}
              />

              {/* 태그 목록 */}
              {formData.tags.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {formData.tags.map((tag, index) => (
                    <span
                      key={index}
                      className="inline-flex items-center px-3 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 text-sm rounded-full"
                    >
                      #{tag}
                      <button
                        type="button"
                        onClick={() => handleTagRemove(tag)}
                        className="ml-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                      >
                        <XMarkIcon className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}

              {/* 도움말 텍스트 */}
              <p className="text-xs text-gray-500 dark:text-gray-400">
                태그는 프롬프트를 분류하고 검색하는 데 도움이 됩니다. 각 태그는
                20자 이내로 입력하세요.
              </p>
            </div>
          </div>

          {/* 프롬프트 내용 */}
          <div className="space-y-2">
            <label className="flex items-center text-sm font-semibold text-gray-800 dark:text-gray-200">
              프롬프트 내용 <span className="text-red-500 ml-1">*</span>
            </label>
            <div className="relative">
              <textarea
                value={formData.prompt_text}
                onChange={(e) => handleChange("prompt_text", e.target.value)}
                rows={12}
                className="w-full px-4 py-3  rounded-xl bg-gray-50 dark:bg-dark-tertiary text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:border-green-500 focus:ring-2 focus:ring-green-500/20 dark:focus:ring-green-500/30 transition-all duration-200 resize-none"
                placeholder="프롬프트 내용을 입력하세요"
                required
              />
              <div className="absolute bottom-3 right-3 text-xs text-gray-500 dark:text-gray-400 flex items-center space-x-2">
                <span>{formData.prompt_text.length} 자</span>
                <span className="text-gray-400 dark:text-gray-500">
                  / 📝 50자 이상 권장
                </span>
              </div>
            </div>
          </div>

          {/* 활성화 옵션 */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="enabled"
              checked={formData.enabled}
              onChange={(e) => handleChange("enabled", e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 rounded"
            />
            <label
              htmlFor="enabled"
              className="ml-2 text-sm text-gray-700 dark:text-gray-300"
            >
              활성화
            </label>
          </div>

          {/* 버튼 영역 */}
          <div className="flex justify-end space-x-3 pt-6 ">
            <button
              type="button"
              onClick={onCancel}
              className="px-6 py-2.5 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700  rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors font-medium"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={!formData.prompt_text.trim()}
              className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 font-medium shadow-lg hover:shadow-xl"
            >
              {initialData ? "수정" : "생성"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PromptCardManager;

import React, { useState } from "react";
import { toast } from "react-hot-toast";
import {
  PlusIcon,
  XMarkIcon,
  BookmarkIcon,
  HashtagIcon,
} from "@heroicons/react/24/outline";
import { projectAPI, handleAPIError } from "../services/api";

const CreateProject = ({ isOpen, onClose, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    tags: [],
  });
  const [tagInput, setTagInput] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      toast.error("프로젝트 이름을 입력해주세요.");
      return;
    }

    try {
      setLoading(true);
      const response = await projectAPI.createProject(formData);
      toast.success("프로젝트가 생성되었습니다!");
      onSuccess?.(response);
      onClose();
    } catch (error) {
      console.error("프로젝트 생성 실패:", error);
      const errorInfo = handleAPIError(error);
      toast.error(errorInfo.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTagAdd = (e) => {
    if (e.key === "Enter" && tagInput.trim()) {
      e.preventDefault();
      const newTag = tagInput.trim();
      if (!formData.tags.includes(newTag)) {
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

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white dark:bg-dark-secondary rounded-2xl max-w-md w-full shadow-xl dark:shadow-none transform transition-all duration-300">
        <div className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900 rounded-lg flex items-center justify-center">
                <BookmarkIcon className="h-5 w-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  새 프로젝트 생성
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  AI 제목 생성 프로젝트를 만들어보세요
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-tertiary transition-colors"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {/* 프로젝트 이름 */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-800 dark:text-gray-200">
              프로젝트 이름 <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, name: e.target.value }))
              }
              className="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-dark-tertiary text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200"
              placeholder="예: 서울경제신문 제목 생성"
              required
            />
          </div>

          {/* 프로젝트 설명 */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-800 dark:text-gray-200">
              프로젝트 설명
            </label>
            <textarea
              value={formData.description}
              onChange={(e) =>
                setFormData((prev) => ({
                  ...prev,
                  description: e.target.value,
                }))
              }
              className="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-dark-tertiary text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 resize-none"
              placeholder="프로젝트에 대한 간단한 설명을 입력하세요"
              rows={4}
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
                className="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-dark-tertiary text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200"
                placeholder="태그를 입력하고 Enter를 누르세요"
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
            </div>
          </div>

          {/* 버튼 */}
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2.5 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-dark-tertiary rounded-lg hover:bg-gray-200 dark:hover:bg-dark-primary transition-colors font-medium"
            >
              취소
            </button>
            <button
              type="submit"
              disabled={loading || !formData.name.trim()}
              className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 font-medium shadow-lg hover:shadow-xl flex items-center gap-2"
            >
              {loading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  생성 중...
                </>
              ) : (
                <>
                  <PlusIcon className="h-4 w-4" />
                  생성하기
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateProject;

import React, { useState, useEffect, useMemo, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import {
  FolderOpenIcon,
  PlusIcon,
  PencilIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  Squares2X2Icon,
  ListBulletIcon,
  XMarkIcon,
  ChevronDownIcon,
  CheckIcon,
} from "@heroicons/react/24/outline";
import { projectAPI, handleAPIError, filterProjects } from "../services/api";
import CreateProject from "./CreateProject";
import { usePrefetch } from "../hooks/usePrefetch";
import { ProjectListSkeleton } from "./skeleton/SkeletonComponents";
import AnimatedProjectCard from "./AnimatedProjectCard";

const ProjectList = () => {
  const navigate = useNavigate();
  const { prefetchProjectDetail, prefetchCreateProject } = usePrefetch();

  // 상태 관리
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("updated");
  const [viewMode, setViewMode] = useState("grid");
  const [sortDropdownOpen, setSortDropdownOpen] = useState(false);
  const sortDropdownRef = useRef(null);

  // 프로젝트 편집 상태
  const [editingProject, setEditingProject] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  // 드롭다운 외부 클릭 감지
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (
        sortDropdownRef.current &&
        !sortDropdownRef.current.contains(event.target)
      ) {
        setSortDropdownOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const loadProjects = async () => {
    try {
      console.log("🔄 loadProjects 시작");
      setLoading(true);
      setError(null);
      const data = await projectAPI.getProjects();
      const projectsWithStats = data.projects || [];
      console.log("📊 로드된 프로젝트 수:", projectsWithStats.length);
      console.log("📋 프로젝트 목록:", projectsWithStats);

      setProjects(projectsWithStats);
    } catch (err) {
      const errorInfo = handleAPIError(err);
      setError(errorInfo.message);
      toast.error(errorInfo.message);
    } finally {
      setLoading(false);
    }
  };

  const deleteProject = async (projectId, projectName) => {
    if (!window.confirm(`"${projectName}" 프로젝트를 삭제하시겠습니까?`)) {
      return;
    }

    // 낙관적 업데이트: 즉시 UI에서 프로젝트 제거
    const originalProjects = [...projects];
    const updatedProjects = projects.filter((p) => p.projectId !== projectId);
    setProjects(updatedProjects);

    // 즉시 성공 토스트 표시
    toast.success("프로젝트가 삭제되었습니다");

    try {
      // 백그라운드에서 실제 삭제 진행
      await projectAPI.deleteProject(projectId);
      console.log("프로젝트 삭제 성공:", projectId);
    } catch (err) {
      console.error("프로젝트 삭제 오류:", err);

      // 실패 시 원래 상태로 복원
      setProjects(originalProjects);

      let errorMessage = "프로젝트 삭제에 실패했습니다";

      if (err.response?.status === 403) {
        errorMessage =
          "삭제 권한이 없습니다. S3 파일 삭제 권한을 확인해주세요.";
      } else if (err.response?.status === 404) {
        errorMessage = "이미 삭제된 프로젝트입니다";
        // 404의 경우 실제로는 삭제된 것이므로 복원하지 않음
        return;
      } else if (err.response) {
        errorMessage =
          err.response.data?.message || `서버 오류 (${err.response.status})`;
      } else if (err.request) {
        errorMessage = "네트워크 오류: CORS 또는 연결 문제";
      }

      toast.error(errorMessage);
    }
  };

  // 프로젝트 편집 함수들
  const handleEditProject = (project) => {
    setEditingProject(project);
    setShowEditModal(true);
  };

  const handleUpdateProject = async (projectData) => {
    try {
      await projectAPI.updateProject(editingProject.projectId, projectData);
      toast.success("프로젝트가 수정되었습니다");
      setShowEditModal(false);
      setEditingProject(null);
      loadProjects();
    } catch (err) {
      const errorInfo = handleAPIError(err);
      toast.error(`프로젝트 수정 실패: ${errorInfo.message}`);
    }
  };

  const handleCancelEdit = () => {
    setShowEditModal(false);
    setEditingProject(null);
  };

  // 필터링된 프로젝트 목록
  const filteredProjects = useMemo(() => {
    return filterProjects(projects, {
      searchQuery,
      sortBy,
    });
  }, [projects, searchQuery, sortBy]);

  // 정렬 옵션 데이터
  const sortOptions = [
    { value: "created", label: "생성일순" },
    { value: "updated", label: "수정일순" },
    { value: "name", label: "이름순" },
  ];

  const currentSortOption = sortOptions.find(
    (option) => option.value === sortBy
  );

  if (loading) {
    return <ProjectListSkeleton />;
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">⚠️ 오류가 발생했습니다</div>
        <p className="text-gray-600 mb-6">{error}</p>
        <button
          onClick={loadProjects}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
        >
          다시 시도
        </button>
      </div>
    );
  }

  const handleCreateSuccess = () => {
    console.log("📝 handleCreateSuccess 호출됨 - 프로젝트 목록 새로고침 시작");
    loadProjects(); // 프로젝트 목록 새로고침
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-dark-primary transition-colors duration-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 상단 헤더 제거 (불필요한 소개 영역) */}

        {/* 필터링 바 */}
        <div className="space-y-6">
          {/* 헤더 */}
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
                프로젝트 목록
              </h2>
              <p className="text-gray-600 dark:text-gray-300 mt-1">
                AI 제목 생성 프로젝트를 관리하고 새로운 프로젝트를 생성하세요
              </p>
            </div>
          </div>

          {/* 필터링 바 */}
          <div className="bg-white dark:bg-dark-secondary rounded-xl p-6 shadow-sm transition-colors duration-200">
            <div className="flex flex-col sm:flex-row gap-4">
              {/* 검색바 */}
              <div className="flex-1 relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  placeholder="프로젝트 이름, 설명, 태그로 검색..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-3 rounded-lg bg-white dark:bg-dark-tertiary text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors duration-200 border-0"
                  style={{ border: "none", boxShadow: "none" }}
                />
              </div>

              {/* 정렬 옵션 - 커스텀 드롭다운 */}
              <div className="flex items-center space-x-3">
                <FunnelIcon className="h-5 w-5 text-gray-400 flex-shrink-0" />
                <div className="relative" ref={sortDropdownRef}>
                  <button
                    onClick={() => setSortDropdownOpen(!sortDropdownOpen)}
                    className="flex items-center justify-between pl-4 pr-3 py-3 bg-white dark:bg-dark-tertiary rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 min-w-[140px]"
                  >
                    <div className="flex items-center space-x-2">
                      <span className="text-gray-700 dark:text-gray-300 font-medium">
                        {currentSortOption?.label}
                      </span>
                    </div>
                    <ChevronDownIcon
                      className={`h-4 w-4 text-gray-400 transition-transform duration-200 ${
                        sortDropdownOpen ? "rotate-180" : ""
                      }`}
                    />
                  </button>

                  {/* 드롭다운 메뉴 */}
                  {sortDropdownOpen && (
                    <div className="absolute top-full left-0 mt-1 w-full bg-white dark:bg-dark-tertiary rounded-lg shadow-lg z-50 overflow-hidden">
                      {sortOptions.map((option) => (
                        <button
                          key={option.value}
                          onClick={() => {
                            setSortBy(option.value);
                            setSortDropdownOpen(false);
                          }}
                          className={`w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-dark-secondary transition-colors duration-150 ${
                            sortBy === option.value
                              ? "bg-blue-50 dark:bg-blue-900 text-blue-600 dark:text-blue-400"
                              : "text-gray-700 dark:text-gray-300"
                          }`}
                        >
                          <div className="flex items-center space-x-2">
                            <span className="font-medium">{option.label}</span>
                          </div>
                          {sortBy === option.value && (
                            <CheckIcon className="h-4 w-4 text-blue-600" />
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* 뷰 모드 */}
              <div className="flex items-center space-x-1 bg-gray-100 dark:bg-dark-tertiary rounded-lg p-1">
                <button
                  onClick={() => setViewMode("grid")}
                  className={`p-2 rounded-md transition-all duration-200 ${
                    viewMode === "grid"
                      ? "bg-white dark:bg-dark-secondary text-gray-900 dark:text-white shadow-sm"
                      : "text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-dark-secondary"
                  }`}
                >
                  <Squares2X2Icon className="h-4 w-4" />
                </button>
                <button
                  onClick={() => setViewMode("list")}
                  className={`p-2 rounded-md transition-all duration-200 ${
                    viewMode === "list"
                      ? "bg-white dark:bg-dark-secondary text-gray-900 dark:text-white shadow-sm"
                      : "text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-dark-secondary"
                  }`}
                >
                  <ListBulletIcon className="h-4 w-4" />
                </button>
              </div>

              {/* 새 프로젝트 버튼 */}
              <button
                onClick={() => setShowCreateModal(true)}
                onMouseEnter={prefetchCreateProject}
                className="inline-flex items-center px-6 py-3 bg-blue-600 text-white dark:text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
              >
                <PlusIcon className="h-4 w-4 mr-2 text-white dark:text-white" />
                새 프로젝트
              </button>
            </div>
          </div>

          {/* 프로젝트 목록 */}
          {filteredProjects.length === 0 ? (
            <div className="text-center py-16 bg-white dark:bg-dark-secondary rounded-xl transition-colors duration-200">
              <FolderOpenIcon className="mx-auto h-16 w-16 text-gray-400 mb-4" />
              <h3 className="text-xl font-medium text-gray-900 dark:text-white mb-2">
                {searchQuery
                  ? "조건에 맞는 프로젝트가 없습니다"
                  : "프로젝트가 없습니다"}
              </h3>
              <p className="text-gray-500 dark:text-gray-300 mb-8">
                {searchQuery
                  ? "다른 조건으로 검색해보세요"
                  : "첫 번째 프로젝트를 생성해보세요"}
              </p>
              <button
                onClick={() => setShowCreateModal(true)}
                onMouseEnter={prefetchCreateProject}
                className="inline-flex items-center px-6 py-3 bg-blue-600 text-white dark:text-white rounded-lg hover:bg-blue-700 font-medium"
              >
                <PlusIcon className="h-4 w-4 mr-2 text-white dark:text-white" />
                새 프로젝트 생성
              </button>
            </div>
          ) : (
            <div
              className={
                viewMode === "grid"
                  ? "grid gap-6 md:grid-cols-2 lg:grid-cols-3"
                  : "space-y-4"
              }
            >
              {filteredProjects.map((project) => (
                <AnimatedProjectCard
                  key={project.projectId}
                  project={project}
                  onDelete={deleteProject}
                  onEdit={handleEditProject}
                  viewMode={viewMode}
                  navigate={navigate}
                  onMouseEnter={prefetchProjectDetail}
                />
              ))}
            </div>
          )}

          {/* 새 프로젝트 생성 모달 */}
          <CreateProject
            isOpen={showCreateModal}
            onClose={() => setShowCreateModal(false)}
            onSuccess={handleCreateSuccess}
          />

          {/* 프로젝트 편집 모달 */}
          <ProjectEditModal
            project={editingProject}
            isOpen={showEditModal}
            onSave={handleUpdateProject}
            onCancel={handleCancelEdit}
          />
        </div>
      </div>
    </div>
  );
};

// 프로젝트 편집 모달 컴포넌트
const ProjectEditModal = ({ project, isOpen, onSave, onCancel }) => {
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    tags: [],
  });
  const [tagInput, setTagInput] = useState("");

  useEffect(() => {
    if (project) {
      setFormData({
        name: project.name || "",
        description: project.description || "",
        tags: Array.isArray(project.tags) ? [...project.tags] : [],
      });
    }
  }, [project]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      toast.error("프로젝트 이름을 입력해주세요");
      return;
    }
    onSave(formData);
  };

  const handleModalClose = () => {
    setTagInput("");
    onCancel();
  };

  // 태그 추가 함수
  const addTag = () => {
    const tag = tagInput.trim();
    if (tag && !formData.tags.includes(tag) && formData.tags.length < 10) {
      setFormData({
        ...formData,
        tags: [...formData.tags, tag],
      });
      setTagInput("");
    }
  };

  // 태그 제거 함수
  const removeTag = (tagToRemove) => {
    setFormData({
      ...formData,
      tags: formData.tags.filter((tag) => tag !== tagToRemove),
    });
  };

  // Enter 키로 태그 추가
  const handleTagKeyPress = (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      addTag();
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* 깔끔한 전체 화면 오버레이 */}
      <div
        className="fixed top-0 left-0 right-0 bottom-0 bg-black/50 backdrop-blur-sm transition-opacity"
        style={{
          zIndex: 9999,
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          width: "100vw",
          height: "100vh",
        }}
        onClick={handleModalClose}
        aria-hidden="true"
      />

      {/* 모달 컨테이너 */}
      <div
        className="fixed inset-0 flex items-center justify-center p-4"
        style={{ zIndex: 10000 }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <div className="bg-white dark:bg-dark-secondary rounded-2xl max-w-md w-full shadow-xl dark:shadow-none transform transition-all duration-300">
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-3">
                <PencilIcon className="h-6 w-6 text-gray-600 dark:text-gray-400" />
                <h3
                  id="modal-title"
                  className="text-lg font-semibold text-gray-900 dark:text-white"
                >
                  프로젝트 편집
                </h3>
              </div>
              <button
                onClick={handleModalClose}
                className="text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>

            <div className="overflow-y-auto max-h-[calc(90vh-80px)]">
              <form onSubmit={handleSubmit} className="p-4 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    프로젝트 이름 *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    className="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-dark-tertiary text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 "
                    placeholder="프로젝트 이름을 입력하세요"
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
                      setFormData({ ...formData, description: e.target.value })
                    }
                    className="w-full px-4 py-3 rounded-xl bg-gray-50 dark:bg-dark-tertiary text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 resize-none "
                    placeholder="프로젝트에 대한 간단한 설명을 입력하세요"
                    rows={4}
                  />
                </div>

                {/* 해시태그 */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    태그 ({formData.tags.length}/10)
                  </label>

                  {/* 현재 태그들 */}
                  {formData.tags.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {formData.tags.map((tag, index) => (
                        <span
                          key={index}
                          className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200"
                        >
                          {tag}
                          <button
                            type="button"
                            onClick={() => removeTag(tag)}
                            className="ml-2 text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200"
                          >
                            <XMarkIcon className="h-3 w-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}

                  {/* 태그 입력 */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={tagInput}
                      onChange={(e) => setTagInput(e.target.value)}
                      onKeyPress={handleTagKeyPress}
                      className="flex-1 px-4 py-3 rounded-xl bg-gray-50 dark:bg-dark-tertiary text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all duration-200 "
                      placeholder="태그를 입력하세요"
                      maxLength={20}
                    />
                    <button
                      type="button"
                      onClick={addTag}
                      disabled={!tagInput.trim() || formData.tags.length >= 10}
                      className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      추가
                    </button>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    태그는 최대 10개까지 추가할 수 있습니다. 각 태그는 20자
                    이내로 입력하세요.
                  </p>
                </div>

                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={handleModalClose}
                    className="px-6 py-2.5 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-dark-tertiary rounded-lg hover:bg-gray-200 dark:hover:bg-dark-primary transition-colors duration-200 font-medium"
                  >
                    취소
                  </button>
                  <button
                    type="submit"
                    disabled={!formData.name.trim()}
                    className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 font-medium shadow-lg hover:shadow-xl"
                  >
                    저장
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default ProjectList;

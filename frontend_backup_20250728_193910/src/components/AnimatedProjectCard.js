import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  DocumentTextIcon,
  EllipsisHorizontalIcon,
  PencilIcon,
  TrashIcon,
  CalendarIcon,
  TagIcon,
} from "@heroicons/react/24/outline";
import { useTheme } from "../contexts/ThemeContext";

const AnimatedProjectCard = ({
  project,
  onDelete,
  onEdit,
  viewMode,
  navigate,
  onMouseEnter,
}) => {
  const [showMenu, setShowMenu] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const { isDark } = useTheme();
  const menuRef = useRef(null);

  const handleCardClick = (e) => {
    if (e.target.closest("button") || e.target.closest("a")) {
      return;
    }
    navigate(`/projects/${project.projectId}`);
  };

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  const cardVariants = {
    initial: {
      scale: 1,
      y: 0,
      boxShadow:
        "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)",
    },
    hover: {
      scale: 1.02,
      y: -4,
      boxShadow:
        "0 10px 25px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 20,
      },
    },
    tap: {
      scale: 0.98,
      transition: {
        type: "spring",
        stiffness: 400,
        damping: 25,
      },
    },
  };

  const iconVariants = {
    initial: { scale: 1, rotate: 0 },
    hover: {
      scale: 1.1,
      rotate: 5,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 20,
      },
    },
  };

  const menuVariants = {
    hidden: {
      opacity: 0,
      scale: 0.95,
      y: -10,
      transition: {
        duration: 0.1,
      },
    },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 25,
      },
    },
  };

  const tagVariants = {
    initial: { opacity: 0, x: -10 },
    animate: (i) => ({
      opacity: 1,
      x: 0,
      transition: {
        delay: i * 0.1,
        type: "spring",
        stiffness: 300,
        damping: 25,
      },
    }),
    hover: {
      scale: 1.05,
      transition: {
        type: "spring",
        stiffness: 400,
        damping: 20,
      },
    },
  };

  return (
    <motion.div
      variants={cardVariants}
      initial="initial"
      whileHover="hover"
      whileTap="tap"
      onHoverStart={() => {
        setIsHovered(true);
        if (onMouseEnter) onMouseEnter();
      }}
      onHoverEnd={() => setIsHovered(false)}
      onClick={handleCardClick}
      className="bg-white dark:bg-dark-secondary rounded-xl transition-colors duration-300 cursor-pointer h-[280px] flex flex-col overflow-hidden"
    >
      <div className="p-6 flex flex-col flex-1">
        <div className="flex justify-between items-start mb-4">
          <div className="flex items-center space-x-3">
            <motion.div variants={iconVariants} className="flex-shrink-0">
              <DocumentTextIcon className="h-8 w-8 text-blue-600 dark:text-blue-400" />
            </motion.div>
            <div>
              <motion.h3
                className="text-lg font-semibold text-gray-900 dark:text-white truncate"
                animate={{
                  color: isHovered ? "#3B82F6" : isDark ? "#ffffff" : "#111827",
                }}
                transition={{ duration: 0.2 }}
              >
                {project.name}
              </motion.h3>
              <p className="text-sm text-gray-500 dark:text-gray-300 mt-1 line-clamp-2">
                {project.description || "설명 없음"}
              </p>
            </div>
          </div>

          <div className="relative" ref={menuRef}>
            <motion.button
              onClick={() => setShowMenu(!showMenu)}
              className="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded-lg hover:bg-gray-100 dark:hover:bg-dark-tertiary transition-colors border-0 shadow-none"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.95 }}
              title="프로젝트 옵션"
              style={{ border: "none", boxShadow: "none" }}
            >
              <EllipsisHorizontalIcon className="h-5 w-5" />
            </motion.button>

            <AnimatePresence>
              {showMenu && (
                <motion.div
                  variants={menuVariants}
                  initial="hidden"
                  animate="visible"
                  exit="hidden"
                  className="absolute right-0 mt-2 w-48 bg-white dark:bg-dark-tertiary rounded-lg shadow-lg ring-1 ring-black ring-opacity-5 z-10"
                >
                  <div className="py-1">
                    <motion.button
                      onClick={() => {
                        onEdit(project);
                        setShowMenu(false);
                      }}
                      className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-dark-secondary"
                      whileHover={{ x: 4 }}
                      transition={{
                        type: "spring",
                        stiffness: 300,
                        damping: 25,
                      }}
                    >
                      <PencilIcon className="h-4 w-4 mr-3" />
                      편집
                    </motion.button>
                    <motion.button
                      onClick={() => {
                        onDelete(project.projectId, project.name);
                        setShowMenu(false);
                      }}
                      className="flex items-center w-full px-4 py-2 text-sm text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
                      whileHover={{ x: 4 }}
                      transition={{
                        type: "spring",
                        stiffness: 300,
                        damping: 25,
                      }}
                    >
                      <TrashIcon className="h-4 w-4 mr-3" />
                      삭제
                    </motion.button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {/* 날짜 */}
          <motion.div
            className="flex items-center space-x-4 mb-3"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <div className="flex items-center text-sm text-gray-500 dark:text-gray-300">
              <CalendarIcon className="h-4 w-4 mr-1.5" />
              <span>
                생성 {new Date(project.createdAt).toLocaleDateString("ko-KR")}
              </span>
            </div>
            {project.updatedAt && project.updatedAt !== project.createdAt && (
              <div className="flex items-center text-sm text-gray-500 dark:text-gray-300">
                <span className="text-gray-300 dark:text-gray-600">•</span>
                <span className="ml-1.5">
                  수정 {new Date(project.updatedAt).toLocaleDateString("ko-KR")}
                </span>
              </div>
            )}
          </motion.div>

          {/* 프롬프트 정보 */}
          <motion.div
            className="flex items-center space-x-4 mb-3"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="flex items-center text-sm text-gray-500 dark:text-gray-300">
              <DocumentTextIcon className="h-4 w-4 mr-1.5" />
              <span>프롬프트 클릭해 주세요</span>
            </div>
          </motion.div>

          {/* 태그 */}
          {project.tags && project.tags.length > 0 && (
            <motion.div
              className="mb-4"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
            >
              <div className="flex items-center">
                <TagIcon className="h-4 w-4 mr-1.5 text-gray-400 dark:text-gray-500" />
                <div className="flex flex-wrap gap-1.5">
                  {project.tags.slice(0, 3).map((tag, index) => (
                    <motion.span
                      key={index}
                      custom={index}
                      variants={tagVariants}
                      initial="initial"
                      animate="animate"
                      whileHover="hover"
                      className="inline-flex items-center bg-gray-100 dark:bg-dark-tertiary text-gray-600 dark:text-gray-300 px-2.5 py-1 rounded-full text-xs font-medium"
                    >
                      {tag}
                    </motion.span>
                  ))}
                  {project.tags.length > 3 && (
                    <motion.span
                      className="inline-flex items-center text-xs text-gray-400 dark:text-gray-500 px-2"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: 0.5 }}
                    >
                      +{project.tags.length - 3}개
                    </motion.span>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </div>

        {/* 호버 시 표시되는 추가 정보 - 고정 높이 */}
        <div className="h-6 flex items-end">
          <AnimatePresence>
            {isHovered && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                transition={{ duration: 0.2 }}
                className="pt-2 w-full"
              >
                <p className="text-xs text-blue-600 dark:text-blue-400 font-medium">
                  클릭하여 프로젝트 열기 →
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
};

export default AnimatedProjectCard;

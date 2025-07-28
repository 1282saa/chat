import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { projectAPI, handleAPIError } from "../services/api";
import AdminView from "./AdminView";
import UserView from "./UserView";
import { useAuth } from "../contexts/AuthContext";
import { ChatInterfaceSkeleton } from "./skeleton/SkeletonComponents";

const ProjectDetail = () => {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProjectData();
  }, [projectId, navigate]);

  const loadProjectData = async () => {
    try {
      setLoading(true);

      // 일반 사용자인 경우 고정된 프로젝트나 기본 프로젝트를 사용
      let projectData;
      if (user?.role === "user") {
        // 일반 사용자용 기본 프로젝트 사용
        if (projectId && projectId !== "default") {
          try {
            projectData = await projectAPI.getProject(projectId);
          } catch (error) {
            console.log("API 호출 실패, 기본 프로젝트 사용:", error);
            projectData = {
              projectId: "4039d9fc-d318-4903-804e-9cf5bf05ba8e",
              name: "서울경제",
              description: "서울경제신문 AI 제목 생성 시스템",
              promptCards: [],
              createdAt: new Date().toISOString(),
              updatedAt: new Date().toISOString(),
            };
          }
        } else {
          // 기본 프로젝트 직접 생성
          projectData = {
            projectId: "4039d9fc-d318-4903-804e-9cf5bf05ba8e",
            name: "서울경제",
            description: "서울경제신문 AI 제목 생성 시스템",
            promptCards: [],
            createdAt: new Date().toISOString(),
            updatedAt: new Date().toISOString(),
          };
        }
      } else {
        // 관리자인 경우
        try {
          projectData = await projectAPI.getProject(projectId);
        } catch (error) {
          console.error("관리자 프로젝트 로드 실패:", error);
          throw error; // 관리자는 에러를 그대로 전파
        }
      }

      setProject(projectData);
    } catch (error) {
      console.error("프로젝트 로드 실패:", error);
      const errorInfo = handleAPIError(error);
      toast.error(errorInfo.message);

      // 권한에 따른 리다이렉트
      if (user?.role === "admin") {
        navigate("/projects");
      } else {
        navigate("/dashboard");
      }
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <ChatInterfaceSkeleton />;
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center transition-colors duration-200">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
            프로젝트를 찾을 수 없습니다
          </h2>
          <button
            onClick={() => {
              if (user?.role === "admin") {
                navigate("/projects");
              } else {
                navigate("/dashboard");
              }
            }}
            className="inline-flex items-center px-4 py-2 text-sm font-medium rounded-md text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900 hover:bg-blue-200 dark:hover:bg-blue-800 focus:outline-none transition-colors duration-200"
          >
            {user?.role === "admin" ? "프로젝트 목록으로" : "대시보드로"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen w-full bg-gray-50 dark:bg-dark-primary transition-all duration-500">
      {user?.role === "admin" ? (
        // 관리자 모드: 프롬프트 카드 관리 + 채팅
        <AdminView
          projectId={project.projectId || projectId}
          projectName={project.name}
        />
      ) : (
        // 사용자 모드: 채팅만
        <UserView
          projectId={project.projectId || projectId}
          projectName={project.name}
        />
      )}
    </div>
  );
};

export default ProjectDetail;

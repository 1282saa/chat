import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { handleAPIError } from "../services/api";
import { useAuth } from "../contexts/AuthContext";

const Login = ({ onLoginSuccess, onSwitchToSignup }) => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    console.log("🚀 handleSubmit 함수 호출됨!");
    e.preventDefault();
    
    console.log("📝 폼 데이터 확인:", formData);
    console.log("⚡ login 함수 존재 여부:", typeof login);
    
    setLoading(true);
    setError("");

    try {
      console.log("🔄 로그인 함수 호출 시작...");
      const response = await login(formData);
      console.log("✅ 로그인 성공:", response);

      if (onLoginSuccess) {
        onLoginSuccess(response);
      }
    } catch (error) {
      console.error("❌ 로그인 오류:", error);
      console.error("❌ 오류 상세:", {
        name: error.name,
        message: error.message,
        stack: error.stack
      });
      
      const apiError = await handleAPIError(error);
      console.log("🔍 처리된 API 오류:", apiError);
      
      // 리다이렉트가 필요한 경우 (401 오류 등)
      if (apiError.shouldRedirect) {
        return;
      }
      
      // 이메일 인증이 필요한 경우 인증 페이지로 리다이렉트
      if (error.name === "UserNotConfirmedException" || (apiError.userMessage && apiError.userMessage.includes("이메일 인증"))) {
        console.log("📧 이메일 인증 페이지로 리다이렉트");
        navigate(`/verify?email=${encodeURIComponent(formData.email)}`);
        return;
      }
      
      setError(apiError.userMessage || error.message || "로그인에 실패했습니다.");
    } finally {
      console.log("🏁 로그인 처리 완료, loading 해제");
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
            로그인
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-300">
            TITLE-NOMICS AI 제목 생성 시스템
          </p>
        </div>

        <form 
          className="mt-8 space-y-6" 
          onSubmit={(e) => {
            console.log("📋 폼 제출 이벤트 발생!");
            handleSubmit(e);
          }}
        >
          <div className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                이메일
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                value={formData.email}
                onChange={handleInputChange}
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white bg-white dark:bg-gray-700 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm transition-colors duration-200"
                placeholder="이메일 주소"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                비밀번호
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                value={formData.password}
                onChange={handleInputChange}
                className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white bg-white dark:bg-gray-700 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm transition-colors duration-200"
                placeholder="비밀번호"
              />
            </div>
          </div>

          {error && (
            <div className="bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded relative">
              {error}
            </div>
          )}

          <div>
            <button
              type="submit"
              disabled={loading}
              onClick={() => console.log("🖱️ 로그인 버튼 클릭됨!")}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "로그인 중..." : "로그인"}
            </button>
          </div>

          <div className="text-center space-y-2">
            <button
              type="button"
              onClick={() => navigate('/forgot-password')}
              className="text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 text-sm transition-colors duration-200 block"
            >
              비밀번호를 잊으셨나요?
            </button>
            <button
              type="button"
              onClick={onSwitchToSignup || (() => navigate('/signup'))}
              className="text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 text-sm transition-colors duration-200 block"
            >
              계정이 없으신가요? 회원가입
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;

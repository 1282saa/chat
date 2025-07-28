import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { authAPI, handleAPIError } from "../services/api";

const EmailVerification = ({ email: propEmail, onVerificationSuccess, onBackToLogin }) => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const emailFromUrl = searchParams.get('email');
  const email = propEmail || emailFromUrl;
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resendLoading, setResendLoading] = useState(false);

  useEffect(() => {
    if (!email) {
      navigate('/login');
    }
  }, [email, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await authAPI.verifyEmail({
        email: email,
        code: code,
      });

      console.log("이메일 인증 성공:", response);

      if (onVerificationSuccess) {
        onVerificationSuccess(response);
      } else {
        // URL 파라미터로 접근한 경우 로그인 페이지로 이동
        navigate('/login');
      }
    } catch (error) {
      const apiError = handleAPIError(error);
      setError(apiError.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    setResendLoading(true);
    setError("");

    try {
      // 인증 코드 재전송을 위해 회원가입 재호출
      await authAPI.signup({ email: email, password: "dummy", fullname: "" });
      alert("인증 코드가 다시 전송되었습니다.");
    } catch (error) {
      const apiError = handleAPIError(error);
      if (apiError.message.includes("이미 존재")) {
        alert("인증 코드가 다시 전송되었습니다.");
      } else {
        setError(apiError.message);
      }
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900 dark:text-white">
            이메일 인증
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600 dark:text-gray-300">
            <span className="font-medium">{email}</span>로<br />
            인증 코드가 전송되었습니다.
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div>
            <label
              htmlFor="code"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300"
            >
              인증 코드 (6자리)
            </label>
            <input
              id="code"
              name="code"
              type="text"
              required
              maxLength={6}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              className="mt-1 appearance-none relative block w-full px-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-white bg-white dark:bg-gray-700 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-center text-2xl font-mono tracking-widest sm:text-sm transition-colors duration-200"
              placeholder="000000"
            />
          </div>

          {error && (
            <div className="bg-red-50 dark:bg-red-900 border border-red-200 dark:border-red-700 text-red-700 dark:text-red-300 px-4 py-3 rounded relative">
              {error}
            </div>
          )}

          <div className="space-y-3">
            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "인증 중..." : "인증 완료"}
            </button>

            <button
              type="button"
              onClick={handleResendCode}
              disabled={resendLoading}
              className="w-full text-center py-2 px-4 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded-md text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
            >
              {resendLoading ? "전송 중..." : "인증 코드 다시 받기"}
            </button>
          </div>

          <div className="text-center">
            <button
              type="button"
              onClick={onBackToLogin || (() => navigate('/login'))}
              className="text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300 text-sm transition-colors duration-200"
            >
              로그인으로 돌아가기
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EmailVerification;

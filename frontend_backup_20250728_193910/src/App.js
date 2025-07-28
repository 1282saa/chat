import React, { Suspense } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useLocation,
} from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { AppProvider } from "./contexts/AppContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { ConversationProvider } from "./contexts/ConversationContext";
import Header from "./components/Header";
import "./App.css";

// 코드 스플리팅 - 필요할 때만 로드
const Login = React.lazy(() => import("./components/Login"));
const Signup = React.lazy(() => import("./components/Signup"));
const ForgotPassword = React.lazy(() => import("./components/ForgotPassword"));
const EmailVerification = React.lazy(() =>
  import("./components/EmailVerification")
);
const ProjectList = React.lazy(() => import("./components/ProjectList"));
const ProjectDetail = React.lazy(() => import("./components/ProjectDetail"));
const CreateProject = React.lazy(() => import("./components/CreateProject"));
const Dashboard = React.lazy(() => import("./pages/Dashboard"));
const Profile = React.lazy(() => import("./pages/Dashboard/Profile"));
const Plan = React.lazy(() => import("./pages/Dashboard/Plan"));

// 빠른 로딩을 위한 미니멀 스켈레톤 컴포넌트
const PageSkeleton = () => (
  <div className="min-h-screen bg-gray-50 dark:bg-dark-primary animate-pulse">
    <div className="bg-white dark:bg-dark-secondary">
      <div className="max-w-7xl mx-auto px-4 py-4">
        <div className="h-6 bg-gray-200 dark:bg-dark-tertiary rounded w-32"></div>
      </div>
    </div>
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="space-y-4">
        <div className="h-4 bg-gray-200 dark:bg-dark-tertiary rounded w-3/4"></div>
        <div className="h-4 bg-gray-200 dark:bg-dark-tertiary rounded w-1/2"></div>
        <div className="h-4 bg-gray-200 dark:bg-dark-tertiary rounded w-5/6"></div>
      </div>
    </div>
  </div>
);

// 보호된 라우트 컴포넌트
const ProtectedRoute = ({ children, requiredRole = null }) => {
  const { isAuthenticated, user, loading } = useAuth();

  if (loading) {
    return <PageSkeleton />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && user?.role !== requiredRole) {
    // 권한이 없으면 해당 역할의 기본 페이지로 리다이렉트
    if (user?.role === "admin") {
      return <Navigate to="/projects" replace />;
    } else {
      return <Navigate to="/dashboard" replace />;
    }
  }

  return children;
};

// 권한별 리다이렉트 컴포넌트
const RoleBasedRedirect = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return <PageSkeleton />;
  }

  if (user?.role === "admin") {
    return <Navigate to="/projects" replace />;
  } else {
    return <Navigate to="/chat" replace />;
  }
};

function AppContent() {
  const location = useLocation();
  const { isAuthenticated } = useAuth();

  // Header를 숨길 경로들: 로그인 관련 페이지만
  const hideHeaderPaths = ["/login", "/signup", "/forgot-password", "/verify"];
  const isHeaderHidden = hideHeaderPaths.includes(location.pathname);
  
  // 전체 화면을 사용하는 페이지들 (padding 없음)
  const fullScreenPaths = location.pathname.startsWith("/projects/") || location.pathname === "/chat";
  const isFullScreen = fullScreenPaths;

  const needsScroll = ['/dashboard', '/dashboard/profile', '/dashboard/plan', '/admin'].includes(location.pathname);
  
  return (
    <div className={`h-screen bg-gray-50 dark:bg-dark-primary transition-colors duration-300 ${needsScroll ? 'overflow-y-auto' : 'overflow-hidden'}`}>
      {isAuthenticated && !isHeaderHidden && <Header />}
      <main
        className={
          isHeaderHidden || !isAuthenticated
            ? ""
            : isFullScreen
            ? "bg-gray-50 dark:bg-dark-primary"
            : "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 bg-gray-50 dark:bg-dark-primary"
        }
      >
        <Suspense fallback={<PageSkeleton />}>
          <Routes>
            {/* 공개 라우트 */}
            <Route
              path="/login"
              element={isAuthenticated ? <RoleBasedRedirect /> : <Login />}
            />
            <Route
              path="/signup"
              element={isAuthenticated ? <RoleBasedRedirect /> : <Signup />}
            />
            <Route
              path="/forgot-password"
              element={isAuthenticated ? <RoleBasedRedirect /> : <ForgotPassword />}
            />
            <Route path="/verify" element={<EmailVerification />} />

            {/* 보호된 라우트 */}
            <Route
              path="/projects"
              element={
                <ProtectedRoute requiredRole="admin">
                  <ProjectList />
                </ProtectedRoute>
              }
            />
            <Route
              path="/create"
              element={
                <ProtectedRoute requiredRole="admin">
                  <CreateProject />
                </ProtectedRoute>
              }
            />
            <Route
              path="/projects/:projectId"
              element={
                <ProtectedRoute requiredRole="admin">
                  <ProjectDetail />
                </ProtectedRoute>
              }
            />

            {/* 일반 사용자 라우트 */}
            <Route
              path="/chat"
              element={
                <ProtectedRoute>
                  <ProjectDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/profile"
              element={
                <ProtectedRoute>
                  <Profile />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard/plan"
              element={
                <ProtectedRoute>
                  <Plan />
                </ProtectedRoute>
              }
            />

            {/* 루트 경로 처리 */}
            <Route
              path="/"
              element={
                isAuthenticated ? (
                  <RoleBasedRedirect />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />

            {/* 404 처리 */}
            <Route
              path="*"
              element={
                isAuthenticated ? (
                  <RoleBasedRedirect />
                ) : (
                  <Navigate to="/login" replace />
                )
              }
            />
          </Routes>
        </Suspense>
      </main>
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ConversationProvider>
          <AppProvider>
            <Router>
              <AppContent />
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                className: "dark:bg-gray-800 dark:text-white",
                style: {
                  background: "var(--toaster-bg, #ffffff)",
                  color: "var(--toaster-color, #374151)",
                  border: "1px solid var(--toaster-border, #e5e7eb)",
                },
                success: {
                  className: "dark:bg-gray-800 dark:text-green-400",
                  style: {
                    background: "var(--toaster-success-bg, #f0fdf4)",
                    color: "var(--toaster-success-color, #15803d)",
                    border: "1px solid var(--toaster-success-border, #bbf7d0)",
                  },
                },
                error: {
                  className: "dark:bg-gray-800 dark:text-red-400",
                  style: {
                    background: "var(--toaster-error-bg, #fef2f2)",
                    color: "var(--toaster-error-color, #dc2626)",
                    border: "1px solid var(--toaster-error-border, #fecaca)",
                  },
                },
              }}
            />
          </Router>
        </AppProvider>
      </ConversationProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;

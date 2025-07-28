// 코드 스플리팅 - 필요할 때만 로드
const Login = React.lazy(() => import("./components/Login"));
const Signup = React.lazy(() => import("./components/Signup"));
const ForgotPassword = React.lazy(() => import("./components/ForgotPassword"));
const EmailVerification = React.lazy(() =>
  import("./components/EmailVerification")
);
// 🗑️ 제거: 프로젝트 관리 관련 컴포넌트들
// const ProjectList = React.lazy(() => import("./components/ProjectList"));
// const ProjectDetail = React.lazy(() => import("./components/ProjectDetail"));
// const CreateProject = React.lazy(() => import("./components/CreateProject"));
const Dashboard = React.lazy(() => import("./pages/Dashboard"));
const Profile = React.lazy(() => import("./pages/Dashboard/Profile"));
const Plan = React.lazy(() => import("./pages/Dashboard/Plan"));

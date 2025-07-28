# 🗂️ title-nomics 프론트엔드 정리 계획

## 📊 현재 상황

- **총 파일 수**: 약 50개 이상의 컴포넌트/훅/페이지
- **실제 사용**: 약 20개 정도만 title-nomics에서 활용
- **불필요한 파일**: 약 30개 (60% 정리 가능)

## ✅ 1단계: 안전하게 백업

```bash
# 현재 frontend 디렉토리 전체 백업
cp -r frontend frontend_backup_$(date +%Y%m%d_%H%M%S)
```

## ❌ 2단계: 삭제 대상 파일들

### A. 복잡한 프로젝트 관리 시스템 (title-nomics에서 불필요)

```
components/ProjectList.js              (23KB, 600줄) - 프로젝트 목록
components/ProjectDetail.js            (4.2KB, 129줄) - 프로젝트 상세
components/CreateProject.js            (7.7KB, 204줄) - 프로젝트 생성
components/AnimatedProjectCard.js      (10KB, 328줄) - 프로젝트 카드 애니메이션
```

### B. 복잡한 프롬프트 관리 (단순한 채팅만 필요)

```
components/PromptCardManager.js        (20KB, 557줄) - 프롬프트 카드 관리
```

### C. 복잡한 인증 시스템 (간단한 로그인만 필요)

```
components/Signup.js                   (13KB, 333줄) - 회원가입
components/ForgotPassword.js           (10KB, 259줄) - 비밀번호 찾기
components/EmailVerification.js        (5.3KB, 143줄) - 이메일 인증
```

### D. 관리자/대시보드 (title-nomics에서 불필요)

```
components/AdminView.js                (4.2KB, 98줄) - 관리자 뷰
components/UserView.js                 (1.3KB, 45줄) - 사용자 뷰
pages/Dashboard/index.js               (4.3KB, 142줄) - 대시보드 메인
pages/Dashboard/Profile.js             (10KB, 251줄) - 프로필 관리
pages/Dashboard/Plan.js                (17KB, 387줄) - 플랜 관리
pages/Dashboard/components/            (전체 디렉토리)
```

### E. 사용하지 않는 훅들

```
hooks/useOrchestration.js              (8.7KB, 265줄) - 구버전 오케스트레이션
hooks/usePrefetch.js                   (1.6KB, 51줄) - 프리페치 (사용 여부 확인)
hooks/useTypingAnimation.js            (2.2KB, 84줄) - 현재 사용하지 않음
```

### F. 기타 불필요한 파일들

```
components/TokenMeter.js               (6.2KB, 173줄) - 토큰 사용량 표시
components/chat/ConversationDrawer.js.backup  (20KB) - 백업 파일
test-websocket.html                    (2.4KB) - 테스트 파일
```

## 🎯 3단계: 정리 후 예상 효과

- **파일 수 감소**: 50개 → 20개 (40% 축소)
- **코드 크기 감소**: 약 200KB → 80KB (60% 축소)
- **유지보수성 향상**: 핵심 기능에만 집중 가능
- **빌드 속도 향상**: 불필요한 컴포넌트 로딩 제거

## 🛡️ 4단계: 안전 장치

1. **Git 커밋**: 정리 전 현재 상태 커밋
2. **백업 보관**: `frontend_backup_*` 디렉토리 보관
3. **단계적 삭제**: 한 번에 모든 파일 삭제하지 않고 카테고리별로 진행
4. **테스트 확인**: 각 단계마다 `npm start`로 작동 확인

## 🚀 5단계: App.js 간소화

현재 App.js의 복잡한 라우팅을 title-nomics 맞춤형으로 간소화:

- `/` → 로그인 또는 채팅으로 리다이렉트
- `/login` → 간단한 로그인
- `/chat` → 메인 채팅 (title-nomics 핵심 기능)

## ⚠️ 주의사항

- **한 번에 모든 파일 삭제하지 말 것**
- **각 단계마다 테스트 확인**
- **문제 발생 시 백업에서 즉시 복구**
- **의존성 오류 발생 시 단계별 롤백**

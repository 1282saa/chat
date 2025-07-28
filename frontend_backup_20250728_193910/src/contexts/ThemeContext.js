import React, { createContext, useContext, useState, useEffect } from "react";

const ThemeContext = createContext();

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return context;
};

export const ThemeProvider = ({ children }) => {
  // 시스템 테마 감지 함수
  const getSystemTheme = () => {
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  };

  // 초기 테마 설정 (깜빡임 방지)
  const getInitialTheme = () => {
    const saved = localStorage.getItem("theme");
    if (saved === "dark") return true;
    if (saved === "light") return false;
    if (saved === "system") return getSystemTheme();
    return getSystemTheme(); // 기본값: 시스템 설정 따름
  };

  const [isDarkMode, setIsDarkMode] = useState(getInitialTheme);
  const [themeMode, setThemeMode] = useState(() => {
    const saved = localStorage.getItem("theme");
    return saved || "system";
  });

  // 시스템 테마 변화 감지
  useEffect(() => {
    const mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    const handleSystemThemeChange = (e) => {
      if (themeMode === "system") {
        setIsDarkMode(e.matches);
      }
    };

    mediaQuery.addEventListener("change", handleSystemThemeChange);
    return () =>
      mediaQuery.removeEventListener("change", handleSystemThemeChange);
  }, [themeMode]);

  // DOM 클래스 업데이트
  useEffect(() => {
    const root = document.documentElement;
    const themeColorMeta = document.getElementById("theme-color");

    // 깜빡임 방지를 위한 transition 비활성화
    root.style.setProperty("--tw-transition-duration", "0ms");

    if (isDarkMode) {
      root.classList.add("dark");
      // 다크모드 시 어두운 테마 색상
      if (themeColorMeta) {
        themeColorMeta.setAttribute("content", "#111827");
      }
    } else {
      root.classList.remove("dark");
      // 라이트모드 시 밝은 테마 색상
      if (themeColorMeta) {
        themeColorMeta.setAttribute("content", "#ffffff");
      }
    }

    // transition 재활성화
    setTimeout(() => {
      root.style.removeProperty("--tw-transition-duration");
    }, 0);

    // 테마 상태 저장
    localStorage.setItem("theme", themeMode);
    localStorage.setItem("isDarkMode", JSON.stringify(isDarkMode));
  }, [isDarkMode, themeMode]);

  // 테마 토글 함수들
  const toggleDarkMode = () => {
    const newMode = isDarkMode ? "light" : "dark";
    setThemeMode(newMode);
    setIsDarkMode(!isDarkMode);
  };

  const setTheme = (mode) => {
    setThemeMode(mode);
    switch (mode) {
      case "dark":
        setIsDarkMode(true);
        break;
      case "light":
        setIsDarkMode(false);
        break;
      case "system":
        setIsDarkMode(getSystemTheme());
        break;
      default:
        setIsDarkMode(false);
    }
  };

  const value = {
    isDarkMode,
    isDark: isDarkMode, // DarkModeToggle 호환성을 위한 별칭
    theme: themeMode,
    themeMode,
    toggleDarkMode,
    toggleTheme: toggleDarkMode, // DarkModeToggle 호환성을 위한 별칭
    setTheme,
    systemTheme: getSystemTheme(),
  };

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
};

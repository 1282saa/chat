import React from "react";
import { useTheme } from "../contexts/ThemeContext";
import { SunIcon, MoonIcon } from "@heroicons/react/24/outline";

const DarkModeToggle = ({ size = "lg" }) => {
  const { isDark, toggleTheme } = useTheme();

  const sizeClasses = {
    sm: "w-10 h-10",
    md: "w-12 h-12",
    lg: "w-14 h-14",
  };

  const iconSizes = {
    sm: "h-4 w-4",
    md: "h-5 w-5",
    lg: "h-6 w-6",
  };

  return (
    <button
      onClick={toggleTheme}
      className={`${sizeClasses[size]} card-neo flex items-center justify-center group transition-all duration-300 hover:scale-105 active:scale-95`}
      title={isDark ? "라이트 모드로 전환" : "다크 모드로 전환"}
    >
      {/* 다크모드 아이콘 */}
      <div
        className={`
        absolute transition-all duration-300 ease-out
        ${
          isDark
            ? "opacity-100 rotate-0 scale-100"
            : "opacity-0 rotate-180 scale-75"
        }
      `}
      >
        <SunIcon
          className={`${iconSizes[size]} text-amber-500 dark:text-amber-400`}
        />
      </div>

      {/* 라이트모드 아이콘 */}
      <div
        className={`
        absolute transition-all duration-300 ease-out
        ${
          !isDark
            ? "opacity-100 rotate-0 scale-100"
            : "opacity-0 rotate-180 scale-75"
        }
      `}
      >
        <MoonIcon className={`${iconSizes[size]} text-slate-600`} />
      </div>
    </button>
  );
};

export default DarkModeToggle;

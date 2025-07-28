import React, { useState } from "react";
import { Link } from "react-router-dom";
import {
  Bars3Icon,
  XMarkIcon,
  UserIcon,
  CreditCardIcon,
} from "@heroicons/react/24/outline";
import { useAuth } from "../../contexts/AuthContext";
import DarkModeToggle from "./DarkModeToggle";
import MainNavToggle from "./MainNavToggle";
import AvatarMenu from "./AvatarMenu";

const Header = () => {
  const { user } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-999 backdrop-filter backdrop-blur-sm bg-gray-50/95 dark:bg-[#1a1d29]/95 border-b border-gray-200/20 dark:border-gray-700/20 transition-all duration-200 w-full">
      <div className="w-full px-4 sm:px-6 lg:px-8">
        <div className="flex items-center h-16 relative">
          {/* Left: Navigation */}
          <div className="flex items-center space-x-8">
            {/* Mobile menu button */}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden p-2 rounded-md text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
            >
              {isMobileMenuOpen ? (
                <XMarkIcon className="h-6 w-6" />
              ) : (
                <Bars3Icon className="h-6 w-6" />
              )}
            </button>
          </div>

          {/* Right: User Controls */}
          <div className="ml-auto flex items-center space-x-4">
            {/* Main Navigation Toggle - Desktop */}
            {user && (
              <div className="hidden md:block">
                <MainNavToggle />
              </div>
            )}

            {/* Theme Toggle */}
            <DarkModeToggle />

            {/* Avatar Menu */}
            {user && <AvatarMenu />}
          </div>
        </div>

        {/* Mobile Menu */}
        {isMobileMenuOpen && user && (
          <div className="md:hidden border-t border-gray-200 dark:border-gray-700 py-4">
            <div className="space-y-4">
              <MainNavToggle />
              <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
                <div className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400">
                  사용자 정보
                </div>
                <div className="px-4 py-2">
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {user?.name || user?.email?.split("@")[0]}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    {user?.email}
                  </p>
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 mt-1">
                    {user?.role === "admin" ? "관리자" : "사용자"}
                  </span>
                </div>
                <div className="border-t border-gray-200 dark:border-gray-700 pt-2 space-y-1">
                  <Link
                    to="/dashboard/profile"
                    className="flex items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-150"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <UserIcon className="h-4 w-4 mr-3" />
                    프로필
                  </Link>
                  <Link
                    to="/dashboard/plan"
                    className="flex items-center px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors duration-150"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <CreditCardIcon className="h-4 w-4 mr-3" />
                    구독 플랜
                  </Link>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </header>
  );
};

export default Header;

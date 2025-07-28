import React, { useState, useEffect } from "react";
import { useAuth } from "../../contexts/AuthContext";
import MetricCard from "./components/MetricCard";
import QuotaGauge from "./components/QuotaGauge";
import UsageChart from "./components/UsageChart";
import LogTable from "./components/LogTable";
import { getUsage } from "../../services/api";
import { ChartBarIcon, SparklesIcon } from "@heroicons/react/24/outline";

const Dashboard = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [usage, setUsage] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchUsageData = async () => {
      try {
        setLoading(true);
        const data = await getUsage("month");
        setUsage(data);
      } catch (err) {
        setError("사용량 데이터를 불러오는데 실패했습니다.");
        console.error("Usage fetch error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchUsageData();
  }, []);

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="bg-white dark:bg-gray-800 rounded-lg p-6 h-32"
            ></div>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg p-6 h-80"></div>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 h-80"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 px-4 py-3 rounded relative">
        {error}
      </div>
    );
  }

  // Mock data for development
  const mockData = {
    todayRequests: 127,
    todayTokens: 45320,
    monthlyLimit: 1000000,
    monthlyUsed: 523400,
    chartData: Array.from({ length: 30 }, (_, i) => ({
      date: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000)
        .toISOString()
        .split("T")[0],
      tokens: Math.floor(Math.random() * 30000) + 10000,
      requests: Math.floor(Math.random() * 100) + 50,
    })),
    recentLogs: Array.from({ length: 20 }, (_, i) => ({
      id: `log-${i}`,
      timestamp: new Date(Date.now() - i * 60 * 60 * 1000).toISOString(),
      model: [
        "Claude 3 Haiku (APAC)",
        "Claude 3 Sonnet (APAC)",
        "Claude 3.5 Sonnet (APAC)",
      ][Math.floor(Math.random() * 3)],
      tokens: Math.floor(Math.random() * 5000) + 1000,
      duration: Math.floor(Math.random() * 3000) + 500,
      status: Math.random() > 0.1 ? "success" : "error",
    })),
  };

  const data = usage || mockData;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          대시보드
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {user?.name || user?.email?.split("@")[0] || "사용자"}님의 사용 현황을
          확인하세요
        </p>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 gap-6">
        <MetricCard
          title="오늘 호출 수"
          value={data.todayRequests.toLocaleString()}
          icon={ChartBarIcon}
          trend="+12%"
          color="blue"
        />
        <MetricCard
          title="오늘 토큰 수"
          value={data.todayTokens.toLocaleString()}
          icon={SparklesIcon}
          trend="+8%"
          color="green"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Usage Chart - Takes 3 columns on large screens */}
        <div className="lg:col-span-3">
          <UsageChart data={data.chartData} />
        </div>

        {/* Right Column - Quota Gauge only */}
        <div className="lg:col-span-1">
          <QuotaGauge used={data.monthlyUsed} limit={data.monthlyLimit} />
        </div>
      </div>

      {/* Log Table */}
      <div className="mt-6">
        <LogTable logs={data.recentLogs} />
      </div>
    </div>
  );
};

export default Dashboard;

import React, { useState } from 'react';
import { 
  CreditCardIcon,
  BellIcon,
  ShieldCheckIcon,
  XMarkIcon,
  CheckIcon
} from '@heroicons/react/24/outline';

const Plan = () => {
  const [showComingSoon, setShowComingSoon] = useState(false);
  const [showPaymentHistory, setShowPaymentHistory] = useState(false);
  const [showPlanChange, setShowPlanChange] = useState(false);

  const showComingSoonToast = () => {
    setShowComingSoon(true);
    setTimeout(() => setShowComingSoon(false), 3000);
  };

  // Mock subscription data
  const subscriptionData = {
    plan: 'Professional',
    status: 'active',
    billingCycle: 'monthly',
    amount: 99000,
    currency: 'KRW',
    nextBilling: '2025-02-28',
    tokensIncluded: 1000000,
    tokensUsed: 523400,
    features: [
      '월 100만 토큰',
      '우선 지원',
      'API 액세스',
      '고급 분석',
      '팀 협업 도구'
    ]
  };

  // Extended payment history
  const paymentHistory = [
    { date: '2025-01-28', amount: 99000, status: '완료', method: '신용카드', last4: '1234' },
    { date: '2024-12-28', amount: 99000, status: '완료', method: '신용카드', last4: '1234' },
    { date: '2024-11-28', amount: 99000, status: '완료', method: '신용카드', last4: '1234' },
    { date: '2024-10-28', amount: 99000, status: '완료', method: '신용카드', last4: '1234' },
    { date: '2024-09-28', amount: 99000, status: '완료', method: '신용카드', last4: '1234' },
    { date: '2024-08-28', amount: 99000, status: '완료', method: '신용카드', last4: '1234' }
  ];

  // Available plans
  const availablePlans = [
    {
      id: 'basic',
      name: 'Basic',
      price: 29000,
      tokens: 100000,
      features: ['월 10만 토큰', '이메일 지원', '기본 분석'],
      current: false
    },
    {
      id: 'professional',
      name: 'Professional',
      price: 99000,
      tokens: 1000000,
      features: ['월 100만 토큰', '우선 지원', 'API 액세스', '고급 분석', '팀 협업 도구'],
      current: true
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: 299000,
      tokens: 5000000,
      features: ['월 500만 토큰', '전용 지원', 'API 액세스', '고급 분석', '팀 협업 도구', '커스텀 통합'],
      current: false
    }
  ];

  return (
    <div className="space-y-6">
      {/* Coming Soon Toast */}
      {showComingSoon && (
        <div className="fixed top-4 right-4 z-50 bg-blue-600 text-white px-4 py-2 rounded-lg shadow-lg transition-all duration-300">
          <div className="flex items-center space-x-2">
            <BellIcon className="h-4 w-4" />
            <span className="text-sm font-medium">Coming Soon!</span>
          </div>
        </div>
      )}

      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">구독 플랜</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          구독 정보와 사용량을 확인하세요
        </p>
      </div>

      {/* Plan Content */}
      <div className="space-y-6">
        <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">현재 구독 플랜</h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              구독 정보와 사용량을 확인하세요
            </p>
          </div>
          <div className="px-6 py-4">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">플랜</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                    {subscriptionData.plan}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">상태</span>
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200">
                    활성
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">청구 주기</span>
                  <span className="text-sm text-gray-900 dark:text-white">월간</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">다음 결제일</span>
                  <span className="text-sm text-gray-900 dark:text-white">{subscriptionData.nextBilling}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">월 요금</span>
                  <span className="text-sm font-bold text-gray-900 dark:text-white">
                    ₩{subscriptionData.amount.toLocaleString()}
                  </span>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700 dark:text-gray-300">토큰 사용량</span>
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      {subscriptionData.tokensUsed.toLocaleString()} / {subscriptionData.tokensIncluded.toLocaleString()}
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700">
                    <div 
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300" 
                      style={{ width: `${(subscriptionData.tokensUsed / subscriptionData.tokensIncluded) * 100}%` }}
                    ></div>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {Math.round((subscriptionData.tokensUsed / subscriptionData.tokensIncluded) * 100)}% 사용됨
                  </p>
                </div>

                <div className="pt-4">
                  <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">포함된 기능</h4>
                  <ul className="space-y-1">
                    {subscriptionData.features.map((feature, index) => (
                      <li key={index} className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                        <ShieldCheckIcon className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            <div className="flex justify-between pt-6 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={() => setShowPlanChange(true)}
                className="px-4 py-2 text-blue-600 dark:text-blue-400 border border-blue-600 dark:border-blue-400 rounded-md hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors duration-200"
              >
                플랜 변경
              </button>
              <button
                onClick={showComingSoonToast}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors duration-200"
              >
                결제 정보 관리
              </button>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">사용량 통계</h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              최근 30일간의 사용량을 확인하세요
            </p>
          </div>
          <div className="px-6 py-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">127</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">오늘 요청</div>
              </div>
              <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">45,320</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">오늘 토큰</div>
              </div>
              <div className="text-center p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">1.2M</div>
                <div className="text-sm text-gray-500 dark:text-gray-400">월간 토큰</div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-800 shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white">결제 내역</h3>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              최근 결제 내역을 확인하세요
            </p>
          </div>
          <div className="px-6 py-4">
            <div className="space-y-4">
              {paymentHistory.slice(0, 3).map((payment, index) => (
                <div key={index} className="flex items-center justify-between py-3 border-b border-gray-200 dark:border-gray-700 last:border-0">
                  <div className="flex items-center space-x-3">
                    <CreditCardIcon className="h-5 w-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        Professional 플랜
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {payment.date}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      ₩{payment.amount.toLocaleString()}
                    </p>
                    <p className="text-xs text-green-600 dark:text-green-400">
                      {payment.status}
                    </p>
                  </div>
                </div>
              ))}
            </div>
            <div className="pt-4">
              <button
                onClick={() => setShowPaymentHistory(true)}
                className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300"
              >
                전체 결제 내역 보기 →
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Payment History Modal */}
      {showPaymentHistory && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4 max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                결제 내역
              </h3>
              <button
                onClick={() => setShowPaymentHistory(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>
            
            <div className="overflow-y-auto max-h-96">
              <div className="space-y-4">
                {paymentHistory.map((payment, index) => (
                  <div key={index} className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                    <div className="flex items-center space-x-3">
                      <CreditCardIcon className="h-5 w-5 text-gray-400" />
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          Professional 플랜
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {payment.date} • {payment.method} **** {payment.last4}
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        ₩{payment.amount.toLocaleString()}
                      </p>
                      <p className="text-xs text-green-600 dark:text-green-400">
                        {payment.status}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Plan Change Modal */}
      {showPlanChange && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-4xl mx-4 max-h-[80vh] overflow-hidden">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                플랜 변경
              </h3>
              <button
                onClick={() => setShowPlanChange(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>
            
            <div className="overflow-y-auto max-h-96">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {availablePlans.map((plan) => (
                  <div key={plan.id} className={`relative border rounded-lg p-6 ${
                    plan.current 
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20' 
                      : 'border-gray-200 dark:border-gray-700'
                  }`}>
                    {plan.current && (
                      <div className="absolute top-4 right-4">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                          현재 플랜
                        </span>
                      </div>
                    )}
                    
                    <div className="text-center">
                      <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                        {plan.name}
                      </h4>
                      <div className="mb-4">
                        <span className="text-3xl font-bold text-gray-900 dark:text-white">
                          ₩{plan.price.toLocaleString()}
                        </span>
                        <span className="text-gray-500 dark:text-gray-400">/월</span>
                      </div>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                        월 {plan.tokens.toLocaleString()} 토큰
                      </p>
                    </div>
                    
                    <ul className="space-y-2 mb-6">
                      {plan.features.map((feature, index) => (
                        <li key={index} className="flex items-center text-sm text-gray-600 dark:text-gray-400">
                          <CheckIcon className="h-4 w-4 text-green-500 mr-2 flex-shrink-0" />
                          {feature}
                        </li>
                      ))}
                    </ul>
                    
                    <button
                      onClick={() => {
                        if (!plan.current) {
                          showComingSoonToast();
                          setShowPlanChange(false);
                        }
                      }}
                      disabled={plan.current}
                      className={`w-full py-2 px-4 rounded-md transition-colors duration-200 ${
                        plan.current
                          ? 'bg-gray-100 text-gray-400 cursor-not-allowed dark:bg-gray-700 dark:text-gray-500'
                          : 'bg-blue-600 text-white hover:bg-blue-700'
                      }`}
                    >
                      {plan.current ? '현재 사용 중' : '플랜 선택'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Plan;
"""
APAC Claude 모델 중앙 관리자
- 서울 리전 최적화 모델 관리
- 성능 기반 동적 모델 선택
- 비용 효율성 고려
- 오류 처리 및 폴백 로직
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger()
logger.setLevel(logging.INFO)

@dataclass
class ModelInfo:
    """APAC 모델 정보"""
    model_id: str
    name: str
    avg_response_time: float
    cost_per_1k_tokens: float
    max_tokens: int
    specialties: List[str]
    recommended_use: str

class APACModelManager:
    """
    APAC 지역 Claude 모델 중앙 관리자
    서울 리전에서 테스트된 성능 데이터 기반
    """
    
    def __init__(self):
        """APAC 모델 관리자 초기화"""
        
        # 실제 테스트된 APAC 모델 정보 (서울 리전 기준)
        self.models = {
            "fast": ModelInfo(
                model_id="apac.anthropic.claude-3-haiku-20240307-v1:0",
                name="Claude 3 Haiku (APAC)",
                avg_response_time=1.89,
                cost_per_1k_tokens=0.25,
                max_tokens=200000,
                specialties=["빠른_응답", "간단_질문", "실시간_처리"],
                recommended_use="간단한 질문, 빠른 응답 필요시"
            ),
            "balanced": ModelInfo(
                model_id="apac.anthropic.claude-3-sonnet-20240229-v1:0",
                name="Claude 3 Sonnet (APAC)",
                avg_response_time=3.22,
                cost_per_1k_tokens=3.0,
                max_tokens=200000,
                specialties=["균형", "일반_질문", "안정성"],
                recommended_use="일반적인 질문, 균형잡힌 성능"
            ),
            "advanced": ModelInfo(
                model_id="apac.anthropic.claude-3-7-sonnet-20250219-v1:0",
                name="Claude 3.7 Sonnet (APAC)",
                avg_response_time=4.17,
                cost_per_1k_tokens=3.0,
                max_tokens=200000,
                specialties=["최신_기술", "정확성", "복잡_분석"],
                recommended_use="복잡한 분석, 최신 기술 활용"
            ),
            "high_performance": ModelInfo(
                model_id="apac.anthropic.claude-3-5-sonnet-20240620-v1:0",
                name="Claude 3.5 Sonnet (APAC)",
                avg_response_time=3.92,
                cost_per_1k_tokens=3.0,
                max_tokens=200000,
                specialties=["고성능", "창의성", "복잡_추론"],
                recommended_use="고품질 답변, 창의적 작업"
            ),
            "premium": ModelInfo(
                model_id="apac.anthropic.claude-sonnet-4-20250514-v1:0",
                name="Claude Sonnet 4 (APAC)",
                avg_response_time=4.48,
                cost_per_1k_tokens=15.0,
                max_tokens=200000,
                specialties=["최고_품질", "전문_분석", "정확성"],
                recommended_use="전문적 분석, 최고 품질 필요시"
            ),
            "latest": ModelInfo(
                model_id="apac.anthropic.claude-3-5-sonnet-20241022-v2:0",
                name="Claude 3.5 Sonnet v2 (APAC)",
                avg_response_time=5.78,
                cost_per_1k_tokens=3.0,
                max_tokens=200000,
                specialties=["최신_기능", "향상된_추론", "멀티모달"],
                recommended_use="최신 기능 활용, 복합 작업"
            )
        }
        
        # 성능 순위 (속도 기준)
        self.speed_ranking = ["fast", "high_performance", "balanced", "advanced", "premium", "latest"]
        
        # 품질 순위 (성능 기준)
        self.quality_ranking = ["premium", "latest", "advanced", "high_performance", "balanced", "fast"]
        
        # 비용 효율성 순위
        self.cost_efficiency_ranking = ["fast", "balanced", "high_performance", "advanced", "latest", "premium"]
        
        logger.info(f"🎯 APACModelManager 초기화 완료 - {len(self.models)}개 모델 관리")
    
    def get_model_by_tier(self, tier: str) -> Optional[ModelInfo]:
        """티어별 모델 정보 반환"""
        return self.models.get(tier)
    
    def get_model_id(self, tier: str) -> str:
        """티어별 모델 ID 반환"""
        model_info = self.models.get(tier)
        if model_info:
            return model_info.model_id
        return self.models["fast"].model_id  # 기본값
    
    def select_optimal_model(self, 
                           complexity: str = "medium",
                           priority: str = "balance", 
                           budget_tier: str = "standard",
                           max_response_time: float = None) -> Tuple[str, ModelInfo]:
        """
        최적 모델 선택
        
        Args:
            complexity: low/medium/high/expert
            priority: speed/balance/quality/cost
            budget_tier: economy/standard/premium
            max_response_time: 최대 허용 응답 시간(초)
        
        Returns:
            (model_tier, ModelInfo)
        """
        
        # 1. 복잡도별 후보 모델
        complexity_candidates = {
            "low": ["fast", "balanced"],
            "medium": ["balanced", "high_performance", "fast"],
            "high": ["advanced", "high_performance", "premium"],
            "expert": ["premium", "latest", "advanced"]
        }
        
        candidates = complexity_candidates.get(complexity, ["balanced"])
        
        # 2. 예산 티어별 필터링
        if budget_tier == "economy":
            candidates = [c for c in candidates if c in ["fast", "balanced"]]
        elif budget_tier == "standard":
            candidates = [c for c in candidates if c not in ["premium"]]
        # premium: 모든 모델 허용
        
        # 3. 응답 시간 제한 적용
        if max_response_time:
            candidates = [c for c in candidates 
                         if self.models[c].avg_response_time <= max_response_time]
        
        # 4. 우선순위별 정렬
        if priority == "speed":
            ranking = self.speed_ranking
        elif priority == "quality":
            ranking = self.quality_ranking
        elif priority == "cost":
            ranking = self.cost_efficiency_ranking
        else:  # balance
            ranking = ["balanced", "high_performance", "fast", "advanced", "latest", "premium"]
        
        # 5. 최적 모델 선택
        for tier in ranking:
            if tier in candidates:
                selected_model = self.models[tier]
                logger.info(f"🎯 모델 선택: {tier} ({selected_model.name}) - "
                           f"복잡도={complexity}, 우선순위={priority}, 예산={budget_tier}")
                return tier, selected_model
        
        # 6. 폴백: 기본 모델
        fallback_tier = "fast"
        fallback_model = self.models[fallback_tier]
        logger.warning(f"⚠️ 조건에 맞는 모델 없음, 기본 모델 사용: {fallback_tier}")
        return fallback_tier, fallback_model
    
    def get_model_for_task(self, task_type: str) -> Tuple[str, ModelInfo]:
        """
        작업 유형별 최적 모델 추천
        
        Args:
            task_type: synthesis/analysis/planning/search/classification
        """
        
        task_mappings = {
            "synthesis": ("balanced", "균형잡힌 답변 생성"),
            "analysis": ("advanced", "심층 분석 필요"),
            "planning": ("fast", "빠른 계획 수립"),
            "search": ("fast", "빠른 검색 결과 처리"),
            "classification": ("fast", "빠른 분류"),
            "expert_analysis": ("premium", "전문적 분석"),
            "creative": ("high_performance", "창의적 작업"),
            "latest_features": ("latest", "최신 기능 활용")
        }
        
        tier, reason = task_mappings.get(task_type, ("balanced", "기본 작업"))
        model_info = self.models[tier]
        
        logger.info(f"📋 작업별 모델 선택: {task_type} → {tier} ({reason})")
        return tier, model_info
    
    def get_all_models(self) -> Dict[str, ModelInfo]:
        """모든 모델 정보 반환"""
        return self.models
    
    def get_model_comparison(self) -> Dict[str, Dict]:
        """모델 비교 정보 반환"""
        comparison = {}
        
        for tier, model in self.models.items():
            comparison[tier] = {
                "name": model.name,
                "model_id": model.model_id,
                "response_time": f"{model.avg_response_time}초",
                "cost": f"${model.cost_per_1k_tokens}/1K 토큰",
                "specialties": model.specialties,
                "recommended_use": model.recommended_use
            }
        
        return comparison
    
    def validate_model_availability(self, model_id: str) -> bool:
        """모델 사용 가능 여부 확인"""
        available_models = [model.model_id for model in self.models.values()]
        return model_id in available_models
    
    def get_environment_config(self) -> Dict[str, str]:
        """환경변수 기반 모델 설정 반환"""
        return {
            "synthesizer_tier": os.environ.get("SYNTHESIZER_MODEL_TIER", "fast"),
            "react_tier": os.environ.get("REACT_MODEL_TIER", "fast"),
            "priority": os.environ.get("SYNTHESIS_PRIORITY", "balance"),
            "apac_enabled": os.environ.get("APAC_MODELS_ENABLED", "true").lower() == "true"
        }

# 전역 모델 매니저 인스턴스
model_manager = APACModelManager()

def get_model_manager() -> APACModelManager:
    """글로벌 모델 매니저 인스턴스 반환"""
    return model_manager 
"""
단순한 프롬프트 관리 시스템
- FAISS 없이 S3에서 직접 프롬프트 로드
- 동적 프롬프트 결합
- 사용자 정의 프롬프트 개수 지원
"""

import json
import boto3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SimplePromptManager:
    """단순하고 효율적인 프롬프트 관리"""
    
    def __init__(self, prompt_bucket: str, prompt_meta_table: str, region: str = 'ap-northeast-2'):
        # Boto3 클라이언트를 매번 새로 생성하여 세션 재사용 문제를 방지합니다.
        session = boto3.session.Session()
        self.s3_client = session.client('s3', region_name=region)
        self.dynamodb = session.resource('dynamodb', region_name=region)
        
        self.prompt_bucket = prompt_bucket
        self.prompt_meta_table = prompt_meta_table
        self.prompt_table = self.dynamodb.Table(prompt_meta_table)
    
    def load_project_prompts(self, project_id: str) -> List[Dict[str, Any]]:
        """프로젝트의 모든 활성화된 프롬프트 카드 로드"""
        try:
            # DynamoDB에서 프로젝트의 활성화된 프롬프트 메타데이터 조회
            response = self.prompt_table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('projectId').eq(project_id) & 
                               boto3.dynamodb.conditions.Attr('isActive').eq(True)
            )
            
            prompt_metas = response.get('Items', [])
            
            if not prompt_metas:
                logger.info(f"프로젝트 {project_id}에 활성화된 프롬프트 카드가 없습니다.")
                return []
            
            # S3에서 실제 프롬프트 내용 로드
            prompts = []
            for meta in prompt_metas:
                try:
                    content = self._load_prompt_content(
                        project_id, 
                        meta['promptId'], 
                        meta.get('s3Key')
                    )
                    
                    if content:
                        prompts.append({
                            'promptId': meta['promptId'],
                            'title': meta.get('title', ''),
                            'content': content,
                            'isActive': meta.get('isActive', True),
                            'createdAt': meta.get('createdAt', ''),
                            'updatedAt': meta.get('updatedAt', '')
                        })
                        
                except Exception as e:
                    logger.warning(f"프롬프트 {meta['promptId']} 로드 실패: {str(e)}")
                    continue
            
            # createdAt으로 정렬
            prompts.sort(key=lambda x: x.get('createdAt', ''))
            
            logger.info(f"프로젝트 {project_id}: {len(prompts)}개 프롬프트 로드 완료")
            return prompts
            
        except Exception as e:
            logger.error(f"프롬프트 로드 오류 (프로젝트: {project_id}): {str(e)}")
            return []
    
    def _load_prompt_content(self, project_id: str, prompt_id: str, s3_key: Optional[str] = None) -> str:
        """S3에서 개별 프롬프트 내용 로드"""
        try:
            # s3Key가 없으면 기본 경로 사용
            if not s3_key:
                s3_key = f"prompts/{project_id}/{prompt_id}/content.txt"
            
            response = self.s3_client.get_object(
                Bucket=self.prompt_bucket,
                Key=s3_key
            )
            
            content = response['Body'].read().decode('utf-8').strip()
            return content
            
        except Exception as e:
            logger.warning(f"S3에서 프롬프트 로드 실패 ({s3_key}): {str(e)}")
            return ""
    
    def combine_prompts(self, prompts: List[Dict[str, Any]], mode: str = "system") -> str:
        """프롬프트들을 결합하여 하나의 시스템 프롬프트 생성"""
        
        if not prompts:
            return ""  # 빈 시스템 프롬프트
        
        if mode == "system":
            # 시스템 프롬프트로 결합 (각 프롬프트를 순서대로 연결)
            system_parts = []
            
            for i, prompt in enumerate(prompts, 1):
                title = prompt.get('title', f'단계 {i}')
                content = prompt.get('content', '').strip()
                
                if content:
                    # 프롬프트에 구분자와 제목 추가
                    if len(prompts) > 1:
                        system_parts.append(f"## {title}")
                    system_parts.append(content)
            
            combined = "\n\n".join(system_parts)
            
        elif mode == "sequential":
            # 순차적 처리용 (각 단계별로 분리)
            combined_parts = []
            for prompt in prompts:
                content = prompt.get('content', '').strip()
                if content:
                    combined_parts.append(content)
            combined = "\n\n---\n\n".join(combined_parts)
            
        else:
            # 단순 연결
            combined = "\n\n".join([p.get('content', '').strip() for p in prompts if p.get('content', '').strip()])
        
        logger.info(f"프롬프트 결합 완료: {len(prompts)}개 → {len(combined)}자 (mode: {mode})")
        return combined
    
    def get_project_prompt_stats(self, project_id: str) -> Dict[str, Any]:
        """프로젝트의 프롬프트 통계 정보"""
        try:
            prompts = self.load_project_prompts(project_id)
            
            total_count = len(prompts)
            total_length = sum(len(p.get('content', '')) for p in prompts)
            average_length = total_length // total_count if total_count > 0 else 0
            
            return {
                "project_id": project_id,
                "total_prompts": total_count,
                "total_length": total_length,
                "average_length": average_length,
                "prompts": [
                    {
                        "id": p['promptId'],
                        "title": p.get('title', ''),
                        "length": len(p.get('content', ''))
                    } for p in prompts
                ],
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"프롬프트 통계 조회 오류: {str(e)}")
            return {
                "project_id": project_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def validate_prompts(self, prompts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """프롬프트 유효성 검사"""
        issues = []
        warnings = []
        
        if not prompts:
            issues.append("활성화된 프롬프트가 없습니다.")
            return {"valid": False, "issues": issues, "warnings": warnings}
        
        # 내용 검사
        for i, prompt in enumerate(prompts):
            content = prompt.get('content', '').strip()
            if not content:
                issues.append(f"프롬프트 {i+1}의 내용이 비어있습니다.")
            elif len(content) < 10:
                warnings.append(f"프롬프트 {i+1}의 내용이 너무 짧습니다. ({len(content)}자)")
            elif len(content) > 10000:
                warnings.append(f"프롬프트 {i+1}의 내용이 매우 깁니다. ({len(content)}자)")
        
        # 전체 길이 검사
        total_length = sum(len(p.get('content', '')) for p in prompts)
        if total_length > 50000:
            warnings.append(f"결합된 프롬프트가 매우 깁니다. ({total_length}자)")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_prompts": len(prompts),
            "total_length": total_length
        } 
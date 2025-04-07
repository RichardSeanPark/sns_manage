from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from app.models.pydantic_models import CollectedData # Pydantic 모델 경로 확인 필요
from app.repository.base import BaseRepository # BaseRepository 경로 확인 필요
from app.repository.data_store import get_repository # get_repository 의존성 주입 함수 경로 확인 필요

router = APIRouter(
    prefix="/api/v1/data",
    tags=["collection_data"],
    responses={404: {"description": "Not found"}},
)

@router.get("/", response_model=List[CollectedData])
async def read_collected_data(
    skip: int = 0,
    limit: int = Query(default=100, le=1000), # 한 번에 최대 1000개 조회 제한
    repository: BaseRepository = Depends(get_repository)
):
    """
    수집된 데이터 목록을 조회합니다.

    - **skip**: 건너뛸 항목 수 (페이지네이션용)
    - **limit**: 반환할 최대 항목 수
    """
    try:
        # 저장소에서 데이터 조회 (get_all_data 메소드 사용)
        # TODO: SQLiteRepository에 get_all_data 메소드 구현 확인 및 추가
        items = await repository.get_all_data(skip=skip, limit=limit) # get_all -> get_all_data 로 수정
        if not items:
            # 데이터가 없는 경우 빈 리스트 반환 (API 명세에 따라 조정 가능)
            return []
        return items
    except Exception as e:
        # 실제 운영 환경에서는 더 구체적인 예외 처리 및 로깅 필요
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

# TODO: 특정 ID로 데이터 조회하는 GET /api/v1/data/{item_id} 엔드포인트 구현 필요

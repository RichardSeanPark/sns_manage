import logging
from typing import List, Optional, Any, Dict

from app.models.collected_data import CollectedData
from app.repository.base import BaseRepository
from app.utils.data_processing import is_title_duplicate

logger = logging.getLogger(__name__)

class InMemoryDataStore(BaseRepository):
    """인메모리 데이터 저장소 구현 (테스트 및 초기 개발용)"""

    def __init__(self):
        self._data: Dict[str, CollectedData] = {}
        logger.info("InMemoryDataStore initialized.")

    async def save_data(self, data: CollectedData, check_duplicates: bool = True, similarity_threshold: float = 0.8) -> Optional[CollectedData]:
        """단일 데이터 항목을 저장합니다. 제목 기반 중복 체크 포함."""
        if not data.title:
            logger.warning(f"Data with ID {data.id} has no title, saving without duplicate check.")
            self._data[data.id] = data
            return data

        if check_duplicates:
            is_duplicate = await self.check_title_exists(data.title, threshold=similarity_threshold)
            if is_duplicate:
                logger.info(f"Duplicate title found for '{data.title}'. Skipping save.")
                # 중복 시 None 반환 또는 기존 데이터 반환 등 정책 결정 필요
                return None 

        logger.debug(f"Saving data with ID: {data.id}, Title: {data.title}")
        self._data[data.id] = data
        return data

    async def save_bulk_data(self, data_list: List[CollectedData]) -> List[CollectedData]:
        """여러 데이터 항목을 한 번에 저장합니다. (개별 중복 체크 미포함 - 필요시 추가)"""
        # TODO: 벌크 저장 시 중복 체크 로직 추가 고려 (성능 영향 있을 수 있음)
        saved_items = []
        for data in data_list:
            # 우선 벌크 저장은 중복 체크 없이 진행
            saved = await self.save_data(data, check_duplicates=False)
            if saved:
                 saved_items.append(saved)
        logger.info(f"Saved {len(saved_items)} items in bulk.")
        return saved_items

    async def get_data_by_id(self, data_id: str) -> Optional[CollectedData]:
        """ID를 기준으로 단일 데이터 항목을 조회합니다."""
        return self._data.get(data_id)

    async def get_all_data(self, limit: int = 100, skip: int = 0) -> List[CollectedData]:
        """모든 데이터 항목을 조회합니다 (페이지네이션 지원)."""
        all_items = list(self._data.values())
        return all_items[skip : skip + limit]

    async def find_data(self, query: Dict[str, Any], limit: int = 100, skip: int = 0) -> List[CollectedData]:
        """주어진 쿼리 조건에 맞는 데이터 항목들을 조회합니다. (간단한 구현)"""
        # TODO: 더 복잡한 쿼리 지원 구현 필요
        results = []
        for item in self._data.values():
            match = True
            for key, value in query.items():
                if not hasattr(item, key) or getattr(item, key) != value:
                    match = False
                    break
            if match:
                results.append(item)
        
        return results[skip : skip + limit]

    async def update_data(self, data_id: str, update_data: Dict[str, Any]) -> Optional[CollectedData]:
        """특정 ID의 데이터 항목을 업데이트합니다."""
        if data_id in self._data:
            existing_data = self._data[data_id]
            updated_data = existing_data.model_copy(update=update_data)
            self._data[data_id] = updated_data
            logger.debug(f"Updated data for ID: {data_id}")
            return updated_data
        logger.warning(f"Data ID not found for update: {data_id}")
        return None

    async def delete_data(self, data_id: str) -> bool:
        """특정 ID의 데이터 항목을 삭제합니다."""
        if data_id in self._data:
            del self._data[data_id]
            logger.debug(f"Deleted data for ID: {data_id}")
            return True
        logger.warning(f"Data ID not found for delete: {data_id}")
        return False

    async def check_title_exists(self, title: str, threshold: float = 0.8) -> bool:
        """주어진 제목과 유사한 제목이 이미 저장소에 있는지 확인합니다."""
        if not title:
            return False
        
        for existing_data in self._data.values():
            if existing_data.title and is_title_duplicate(title, existing_data.title, threshold):
                logger.debug(f"Found similar title for '{title}' (Existing: '{existing_data.title}')")
                return True
        return False

# 전역 저장소 인스턴스 (싱글톤처럼 사용 가능)
data_store: BaseRepository = InMemoryDataStore()

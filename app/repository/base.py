from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
from app.models.collected_data import CollectedData

class BaseRepository(ABC):
    """데이터 저장소의 기본 인터페이스를 정의하는 추상 기본 클래스"""

    @abstractmethod
    async def save_data(self, data: CollectedData) -> CollectedData:
        """단일 데이터 항목을 저장합니다. 중복 처리 로직 포함 가능."""
        pass

    @abstractmethod
    async def save_bulk_data(self, data_list: List[CollectedData]) -> List[CollectedData]:
        """여러 데이터 항목을 한 번에 저장합니다."""
        pass

    @abstractmethod
    async def get_data_by_id(self, data_id: str) -> Optional[CollectedData]:
        """ID를 기준으로 단일 데이터 항목을 조회합니다."""
        pass

    @abstractmethod
    async def get_all_data(self, limit: int = 100, skip: int = 0) -> List[CollectedData]:
        """모든 데이터 항목을 조회합니다 (페이지네이션 지원)."""
        pass

    @abstractmethod
    async def find_data(self, query: Dict[str, Any], limit: int = 100, skip: int = 0) -> List[CollectedData]:
        """주어진 쿼리 조건에 맞는 데이터 항목들을 조회합니다."""
        pass

    @abstractmethod
    async def update_data(self, data_id: str, update_data: Dict[str, Any]) -> Optional[CollectedData]:
        """특정 ID의 데이터 항목을 업데이트합니다."""
        pass

    @abstractmethod
    async def delete_data(self, data_id: str) -> bool:
        """특정 ID의 데이터 항목을 삭제합니다."""
        pass
        
    @abstractmethod
    async def check_title_exists(self, title: str, threshold: float = 0.8) -> bool:
        """주어진 제목과 유사한 제목이 이미 저장소에 있는지 확인합니다."""
        pass

import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# agents 임포트 시도
try:
    from agents import tool # Agents SDK의 tool 데코레이터
except ImportError:
    # 대체 데코레이터 정의
    def tool(func):
        return func
    logger = logging.getLogger(__name__)
    logger.warning("Could not import 'agents' library. Using dummy 'tool' decorator.")

from app.repository.data_store import get_repository # 임포트 경로 수정
from app.models.collected_data import CollectedData # 임포트 경로 수정

logger = logging.getLogger(__name__)

# --- Get Collected Data Tool ---

class GetDataInput(BaseModel):
    query: Optional[Dict[str, Any]] = Field(default=None, description="데이터 필터링을 위한 쿼리 딕셔너리 (예: {'source_type': 'RSS'}). 생략 시 전체 조회.")
    limit: int = Field(default=10, gt=0, le=100, description="반환할 최대 데이터 개수")
    skip: int = Field(default=0, ge=0, description="건너뛸 데이터 개수 (페이지네이션)")

@tool
async def get_collected_data_tool(input_data: GetDataInput) -> List[CollectedData]:
    """
    저장소에서 수집된 데이터 목록을 조회합니다. 필터링 및 페이지네이션을 지원합니다.
    """
    logger.info(f"Tool 'get_collected_data_tool' called with input: {input_data}")
    repository = get_repository()
    try:
        if input_data.query:
            logger.debug(f"Finding data with query: {input_data.query}, limit={input_data.limit}, skip={input_data.skip}")
            items = await repository.find_data(query=input_data.query, limit=input_data.limit, skip=input_data.skip)
        else:
            logger.debug(f"Getting all data with limit={input_data.limit}, skip={input_data.skip}")
            items = await repository.get_all_data(limit=input_data.limit, skip=input_data.skip)

        logger.info(f"Found {len(items)} data items.")
        # Pydantic 모델 리스트 직접 반환 (Agents SDK가 처리)
        return items
    except Exception as e:
        logger.error(f"Error in get_collected_data_tool: {e}", exc_info=True)
        # 에이전트에게 오류를 알리기 위해 빈 리스트 또는 오류 메시지 반환 고려
        # 여기서는 Pydantic 모델을 반환해야 하므로 빈 리스트 반환
        return []

# --- Save Collected Data Tool ---

# save_data_tool은 입력으로 CollectedData 객체 전체를 받는 것이 자연스러움
# Pydantic 모델 자체를 입력 스키마로 사용할 수 있음
@tool
async def save_collected_data_tool(data_to_save: CollectedData) -> Optional[CollectedData]:
    """
    단일 수집 데이터 항목을 저장소에 저장합니다.
    내부적으로 제목 유사도를 검사하여 중복 저장을 방지할 수 있습니다.
    성공 시 저장된 데이터 객체를, 중복 또는 오류 시 None을 반환합니다.
    """
    logger.info(f"Tool 'save_collected_data_tool' called for title: {data_to_save.title}")
    repository = get_repository()
    try:
        # repository.save_data는 기본적으로 중복 체크를 수행함
        saved_data = await repository.save_data(data=data_to_save)
        if saved_data:
            logger.info(f"Data with ID {saved_data.id} saved successfully.")
            return saved_data
        else:
            # 중복 또는 다른 저장 오류일 수 있음
            logger.warning(f"Data with title '{data_to_save.title}' was not saved (likely duplicate or error).")
            return None
    except Exception as e:
        logger.error(f"Error in save_collected_data_tool: {e}", exc_info=True)
        return None

import pytest
from unittest.mock import AsyncMock, patch
from typing import List, Dict, Any, Optional

# 테스트 대상 도구 임포트
from app.agents.tools.data_management_tools import (
    get_collected_data_tool,
    save_collected_data_tool,
    GetDataInput
)
from app.models.collected_data import CollectedData
from app.repository.base import BaseRepository

# 테스트용 샘플 데이터 (test_collection_api.py 와 유사하게 사용 가능)
# tests.api.test_collection_api 모듈이 존재하고 create_sample_data 함수가 있다고 가정
# 경로 문제가 발생하면 sys.path 조정 또는 fixture 형태로 샘플 데이터 제공 필요
try:
    from tests.api.test_collection_api import create_sample_data
except ImportError:
    # 대체 샘플 데이터 생성 함수 (실제 API 테스트와 동일하게 유지 권장)
    from datetime import datetime, timezone
    from app.models.enums import SourceType, ProcessingStatus
    def create_sample_data(count: int) -> List[CollectedData]:
        samples = []
        base_time = datetime.now(timezone.utc)
        for i in range(count):
            samples.append(CollectedData(
                id=f"test-id-{i}",
                source_url=f"http://example.com/{i}",
                source_type=SourceType.RSS,
                collected_at=base_time,
                title=f"Test Title {i}",
                link=f"http://example.com/article/{i}",
                published_at=base_time,
                summary=f"Test Summary {i}",
                content=f"Test Content {i}",
                author=f"Author {i}",
                categories=["AI", "Test"],
                tags=["test", f"sample-{i}"],
                relevance_score=0.8,
                processing_status=ProcessingStatus.PENDING,
                extra_data={"key": f"value{i}"}
            ))
        return samples

# --- Fixtures ---

@pytest.fixture
def mock_repository():
    """모의 BaseRepository 인스턴스를 생성하는 fixture"""
    repo = AsyncMock(spec=BaseRepository)
    # 각 테스트에서 구체적인 반환값 설정 필요
    return repo

@pytest.fixture(autouse=True) # 모든 테스트 함수에 자동으로 적용
def patch_get_repository(mock_repository):
    """get_repository 함수를 모의 객체로 패치하는 fixture"""
    # data_management_tools 모듈 내의 get_repository를 패치
    with patch('app.agents.tools.data_management_tools.get_repository', return_value=mock_repository) as patched:
        yield patched # 패치된 함수 객체를 반환 (필요시 사용)

# --- Tests for get_collected_data_tool ---

@pytest.mark.asyncio
async def test_get_data_no_query(mock_repository: AsyncMock):
    """쿼리 없이 호출 시 get_all_data 호출 및 결과 반환 확인"""
    sample_data = create_sample_data(3)
    mock_repository.get_all_data.return_value = sample_data

    input_data = GetDataInput(limit=5, skip=0) # query=None (기본값)
    result = await get_collected_data_tool(input_data)

    mock_repository.get_all_data.assert_called_once_with(limit=5, skip=0)
    mock_repository.find_data.assert_not_called() # find_data는 호출 안 됨
    assert result == sample_data

@pytest.mark.asyncio
async def test_get_data_with_query(mock_repository: AsyncMock):
    """쿼리 포함 호출 시 find_data 호출 및 결과 반환 확인"""
    sample_data = create_sample_data(2)
    mock_repository.find_data.return_value = sample_data
    test_query = {"source_type": "RSS"}

    input_data = GetDataInput(query=test_query, limit=10, skip=0)
    result = await get_collected_data_tool(input_data)

    mock_repository.find_data.assert_called_once_with(query=test_query, limit=10, skip=0)
    mock_repository.get_all_data.assert_not_called() # get_all_data는 호출 안 됨
    assert result == sample_data

@pytest.mark.asyncio
async def test_get_data_pagination(mock_repository: AsyncMock):
    """페이지네이션 파라미터 전달 확인 (get_all_data) """
    mock_repository.get_all_data.return_value = [] # 결과는 중요하지 않음
    input_data = GetDataInput(limit=7, skip=3)
    await get_collected_data_tool(input_data)
    mock_repository.get_all_data.assert_called_once_with(limit=7, skip=3)

@pytest.mark.asyncio
async def test_get_data_empty_result(mock_repository: AsyncMock):
    """조회 결과 없을 때 빈 리스트 반환 확인"""
    mock_repository.get_all_data.return_value = []
    input_data = GetDataInput()
    result = await get_collected_data_tool(input_data)
    assert result == []

@pytest.mark.asyncio
async def test_get_data_repository_error(mock_repository: AsyncMock, caplog):
    """저장소 오류 발생 시 빈 리스트 반환 및 로그 기록 확인"""
    mock_repository.get_all_data.side_effect = Exception("DB connection error")
    input_data = GetDataInput()
    result = await get_collected_data_tool(input_data)

    assert result == []
    assert "Error in get_collected_data_tool" in caplog.text
    assert "DB connection error" in caplog.text

# --- Tests for save_collected_data_tool ---

@pytest.mark.asyncio
async def test_save_data_success(mock_repository: AsyncMock):
    """새 데이터 저장 성공 시 저장된 객체 반환 확인"""
    new_data = create_sample_data(1)[0]
    # save_data가 성공 시 저장된 객체(또는 동일 객체)를 반환한다고 가정
    mock_repository.save_data.return_value = new_data

    result = await save_collected_data_tool(new_data)

    mock_repository.save_data.assert_called_once_with(data=new_data)
    assert result == new_data

@pytest.mark.asyncio
async def test_save_data_duplicate(mock_repository: AsyncMock, caplog):
    """중복 데이터 저장 시도 시 None 반환 및 로그 기록 확인"""
    duplicate_data = create_sample_data(1)[0]
    # save_data가 중복 시 None을 반환한다고 가정
    mock_repository.save_data.return_value = None

    result = await save_collected_data_tool(duplicate_data)

    mock_repository.save_data.assert_called_once_with(data=duplicate_data)
    assert result is None
    assert "was not saved (likely duplicate or error)" in caplog.text

# Pydantic 모델 자체에서 유효성 검사가 일어나므로, 도구 레벨에서 invalid data 테스트는 생략 가능
# 만약 도구 내에서 추가적인 유효성 검사가 있다면 해당 로직 테스트 필요

@pytest.mark.asyncio
async def test_save_data_repository_error(mock_repository: AsyncMock, caplog):
    """저장소 오류 발생 시 None 반환 및 로그 기록 확인"""
    error_data = create_sample_data(1)[0]
    mock_repository.save_data.side_effect = Exception("DB write error")

    result = await save_collected_data_tool(error_data)

    mock_repository.save_data.assert_called_once_with(data=error_data)
    assert result is None
    assert "Error in save_collected_data_tool" in caplog.text
    assert "DB write error" in caplog.text

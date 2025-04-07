import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock
from typing import List
from datetime import datetime, timezone

# 테스트 대상 FastAPI 앱 임포트
from app.main import app
# Pydantic 모델 임포트
from app.models.collected_data import CollectedData
from app.models.enums import SourceType, ProcessingStatus
# 의존성 주입 함수 임포트
from app.repository.data_store import get_repository
from app.repository.base import BaseRepository

# 테스트용 샘플 데이터 생성 함수
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

# --- Test Cases ---

@pytest.mark.asyncio
async def test_read_collected_data_success():
    """ GET /api/v1/data/ 성공 케이스 """
    mock_repo = AsyncMock(spec=BaseRepository)
    sample_data = create_sample_data(5)
    mock_repo.get_all_data = AsyncMock(return_value=sample_data)
    app.dependency_overrides[get_repository] = lambda: mock_repo

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/data/")

        assert response.status_code == 200
        response_data = response.json()
        assert isinstance(response_data, list)
        assert len(response_data) == 5
        assert response_data[0]["title"] == "Test Title 0"
        try:
            [CollectedData.model_validate(item) for item in response_data]
        except Exception as e:
            pytest.fail(f"Response data validation failed: {e}")
    finally:
        app.dependency_overrides = {} # 오버라이드 정리


@pytest.mark.asyncio
@pytest.mark.parametrize("skip, limit, expected_count, expected_first_id", [
    (0, 2, 2, "test-id-0"),
    (2, 2, 2, "test-id-2"),
    (4, 2, 1, "test-id-4"),
    (0, 10, 5, "test-id-0"),
    (5, 5, 0, None),
])
async def test_read_collected_data_pagination(skip, limit, expected_count, expected_first_id):
    """ GET /api/v1/data/ 페이지네이션 테스트 """
    mock_repo = AsyncMock(spec=BaseRepository)
    sample_data = create_sample_data(5)
    # 페이지네이션 로직을 모의 객체에 반영
    mock_repo.get_all_data = AsyncMock(side_effect=lambda skip=0, limit=100: sample_data[skip:skip+limit])
    app.dependency_overrides[get_repository] = lambda: mock_repo

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(f"/api/v1/data/?skip={skip}&limit={limit}")

        assert response.status_code == 200
        response_data = response.json()
        assert len(response_data) == expected_count
        if expected_count > 0:
            assert response_data[0]["id"] == expected_first_id
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_read_collected_data_empty():
    """ GET /api/v1/data/ 데이터 없는 경우 테스트 """
    mock_repo = AsyncMock(spec=BaseRepository)
    mock_repo.get_all_data = AsyncMock(return_value=[]) # 빈 리스트 반환
    app.dependency_overrides[get_repository] = lambda: mock_repo

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/data/")

        assert response.status_code == 200
        assert response.json() == []
    finally:
        app.dependency_overrides = {}


@pytest.mark.asyncio
async def test_read_collected_data_invalid_limit():
    """ GET /api/v1/data/ 잘못된 limit 파라미터 테스트 """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response_zero = await client.get("/api/v1/data/?limit=0")
        assert response_zero.status_code == 422

        response_large = await client.get("/api/v1/data/?limit=1001")
        assert response_large.status_code == 422


@pytest.mark.asyncio
async def test_read_collected_data_repository_error():
    """ GET /api/v1/data/ 저장소 에러 발생 시 테스트 """
    mock_repo = AsyncMock(spec=BaseRepository)
    mock_repo.get_all_data = AsyncMock(side_effect=Exception("Database connection error")) # 예외 발생
    app.dependency_overrides[get_repository] = lambda: mock_repo

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/data/")

        assert response.status_code == 500
        response_json = response.json()
        assert "Internal server error" in response_json["detail"]
    finally:
        app.dependency_overrides = {}

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import List, Optional
from pydantic import HttpUrl
import httpx # HTTPStatusError, RequestError 임포트를 위해 추가

# 테스트 대상 도구 임포트
from app.agents.tools.collection_tools import (
    collect_rss_feeds_tool,
    crawl_webpage_tool,
    CollectRssInput,
    CrawlInput
)
from app.models.collected_data import CollectedData
from app.models.enums import SourceType, ProcessingStatus

# 테스트용 샘플 데이터 생성 함수 (다른 테스트 파일에서 가져오거나 여기서 정의)
try:
    from tests.api.test_collection_api import create_sample_data
except ImportError:
    from datetime import datetime, timezone
    from app.models.enums import ProcessingStatus
    def create_sample_data(count: int, source_type: SourceType = SourceType.RSS) -> List[CollectedData]:
        # ... (샘플 데이터 생성 로직, source_type 인자 추가) ...
        samples = []
        base_time = datetime.now(timezone.utc)
        for i in range(count):
            samples.append(CollectedData(
                id=f"test-{source_type.value}-id-{i}",
                source_url=f"http://example.com/{source_type.value}/{i}",
                source_type=source_type,
                collected_at=base_time,
                title=f"Test {source_type.value} Title {i}",
                link=f"http://example.com/article/{i}",
                published_at=base_time,
                summary=f"Test Summary {i}",
                content=f"Test Content {i}",
                author=f"Author {i}",
                categories=["AI", "Test"],
                tags=["test", f"sample-{i}"],
                relevance_score=0.8,
                processing_status=ProcessingStatus.RAW, # RAW 상태로 생성
                extra_data={"key": f"value{i}"}
            ))
        return samples


# --- Tests for collect_rss_feeds_tool ---

# parse_rss_feed 함수를 모의 처리하기 위한 patch 데코레이터 사용
@patch('app.agents.tools.collection_tools.parse_rss_feed', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_collect_rss_specific_urls(mock_parse_rss: AsyncMock):
    """특정 URL 입력 시 해당 URL에 대해서만 parse_rss_feed 호출 확인"""
    test_urls = [HttpUrl("http://test.com/rss1"), HttpUrl("http://test.com/rss2")]
    # side_effect에서 생성되는 샘플 데이터의 source_url 지정
    def side_effect_specific(url, category):
        if url == "http://test.com/rss1":
            sample = create_sample_data(1)[0]
            sample.source_url = "http://test.com/rss1"
            return [sample]
        elif url == "http://test.com/rss2":
            sample = create_sample_data(1)[0]
            sample.source_url = "http://test.com/rss2"
            return [sample]
        else:
            return []
    mock_parse_rss.side_effect = side_effect_specific

    input_data = CollectRssInput(target_urls=test_urls)
    result = await collect_rss_feeds_tool(input_data)

    assert mock_parse_rss.call_count == 2
    # 호출 인자 확인 (첫 번째 호출 기준)
    first_call_args = mock_parse_rss.call_args_list[0].args # .args 사용
    assert first_call_args[0] in [str(u) for u in test_urls]
    assert len(result) == 2 # 각 호출이 1개의 샘플 데이터를 반환한다고 가정
    assert result[0].source_url in ["http://test.com/rss1", "http://test.com/rss2"]
    assert result[1].source_url in ["http://test.com/rss1", "http://test.com/rss2"]
    assert result[0].source_url != result[1].source_url


@patch('app.agents.tools.collection_tools.parse_rss_feed', new_callable=AsyncMock)
@patch('app.agents.tools.collection_tools.RSS_SOURCES', [ # 설정된 RSS_SOURCES 모의 처리
    {"url": "http://config.com/rss1", "category": "ConfigCat1"},
    {"url": "http://config.com/rss2", "category": "ConfigCat2"},
])
@pytest.mark.asyncio
async def test_collect_rss_all_urls(mock_parse_rss: AsyncMock):
    """입력 URL 없을 때 설정된 모든 URL에 대해 parse_rss_feed 호출 확인"""
    # side_effect에서 생성되는 샘플 데이터의 source_url 지정
    def side_effect_all(url, category):
        sample = create_sample_data(1)[0]
        sample.source_url = url # 호출된 URL을 source_url로 설정
        return [sample]
    mock_parse_rss.side_effect = side_effect_all

    input_data = CollectRssInput(target_urls=None) # target_urls=None
    result = await collect_rss_feeds_tool(input_data)

    assert mock_parse_rss.call_count == 2 # 설정된 소스 2개
    # 호출 인자 확인 (첫 번째 호출 기준, keyword arguments로 접근)
    first_call = mock_parse_rss.call_args_list[0]
    assert first_call.args[0] == "http://config.com/rss1"
    # category가 위치인자 또는 키워드 인자로 전달될 수 있으므로 둘 다 확인
    if len(first_call.args) > 1:
        assert first_call.args[1] == "ConfigCat1"
    elif 'category' in first_call.kwargs:
        assert first_call.kwargs['category'] == "ConfigCat1"
    assert len(result) == 2
    assert result[0].source_url == "http://config.com/rss1"
    assert result[1].source_url == "http://config.com/rss2"

@patch('app.agents.tools.collection_tools.parse_rss_feed', new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_collect_rss_partial_failure(mock_parse_rss: AsyncMock):
    """일부 피드 파싱 실패 시 성공한 결과만 반환하는지 확인"""
    test_urls = [HttpUrl("http://ok.com/rss"), HttpUrl("http://fail.com/rss")]
    # fail.com URL 호출 시 예외 발생시키도록 설정
    # side_effect는 호출될 때마다 다른 값을 반환하거나 예외를 발생시킬 수 있음
    async def side_effect_partial(url, category):
        if url == "http://ok.com/rss":
            sample = create_sample_data(1)[0]
            sample.source_url = "http://ok.com/rss" # source_url 명시적 설정
            return [sample]
        elif url == "http://fail.com/rss":
            raise Exception("Parsing failed")
        else:
            return []
    mock_parse_rss.side_effect = side_effect_partial

    input_data = CollectRssInput(target_urls=test_urls)
    result = await collect_rss_feeds_tool(input_data)

    assert mock_parse_rss.call_count == 2
    assert len(result) == 1 # 성공한 ok.com의 결과만 포함
    assert result[0].source_url == "http://ok.com/rss" # 수정된 source_url 검증

# --- Tests for crawl_webpage_tool ---

# httpx.AsyncClient를 patch할 때, 올바른 경로 지정이 중요
@patch('app.agents.tools.collection_tools.httpx.AsyncClient')
@pytest.mark.asyncio
async def test_crawl_valid_page(mock_async_client_cls):
    """유효한 페이지 크롤링 성공 시 CollectedData 반환 확인"""
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = "<html><head><title>Test Crawl</title></head><body><p>Main content here.</p><p>Another paragraph.</p></body></html>"
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_async_client_cls.return_value.__aenter__.return_value = mock_client_instance

    test_url = HttpUrl("http://valid.com/page")
    input_data = CrawlInput(url=test_url)
    result = await crawl_webpage_tool(input_data)

    from app.config import USER_AGENT
    mock_client_instance.get.assert_called_once_with(str(test_url), headers={'User-Agent': USER_AGENT})

    # 결과 검증 강화
    assert result is not None, f"crawl_webpage_tool returned None for URL: {test_url}"
    assert isinstance(result, CollectedData), f"Expected CollectedData, got {type(result)}"
    assert result.title == "Test Crawl", f"Expected title 'Test Crawl', got '{result.title}'"
    assert str(result.source_url) == str(test_url)
    assert result.source_type == SourceType.CRAWLING
    assert result.content is not None, "Content is None."
    # body 태그 내 p 태그 내용 추출 확인
    assert "Main content here." in result.content, "Expected content 'Main content here.' not found."
    assert "Another paragraph." in result.content, "Expected content 'Another paragraph.' not found."
    assert result.processing_status == ProcessingStatus.RAW # RAW 상태 확인

@patch('app.agents.tools.collection_tools.httpx.AsyncClient')
@pytest.mark.asyncio
async def test_crawl_invalid_url(mock_async_client_cls, caplog):
    """잘못된 URL 또는 HTTP 오류 시 None 반환 및 로그 기록 확인"""
    # --- HTTP 404 오류 시나리오 ---
    mock_response_404 = MagicMock(spec=httpx.Response)
    mock_response_404.status_code = 404
    mock_response_404.reason_phrase = "Not Found"
    mock_response_404.request = MagicMock(spec=httpx.Request)
    # raise_for_status가 HTTPStatusError를 발생시키도록 설정
    mock_response_404.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("Not Found", request=mock_response_404.request, response=mock_response_404))

    mock_client_instance_404 = AsyncMock()
    mock_client_instance_404.get = AsyncMock(return_value=mock_response_404)
    mock_async_client_cls.return_value.__aenter__.return_value = mock_client_instance_404

    url_404 = HttpUrl("http://notfound.com")
    input_404 = CrawlInput(url=url_404)
    result_404 = await crawl_webpage_tool(input_404)

    assert result_404 is None
    assert "HTTP error occurred" in caplog.text
    assert "404 - Not Found" in caplog.text
    caplog.clear()

    # --- 요청 오류 시나리오 ---
    mock_client_instance_req_err = AsyncMock()
    mock_client_instance_req_err.get = AsyncMock(side_effect=httpx.RequestError("DNS lookup failed"))
    mock_async_client_cls.return_value.__aenter__.return_value = mock_client_instance_req_err

    url_req_err = HttpUrl("http://invalid-domain-for-test.xyz")
    input_req_err = CrawlInput(url=url_req_err)
    result_req_err = await crawl_webpage_tool(input_req_err)

    assert result_req_err is None
    assert "Request error occurred" in caplog.text
    assert "DNS lookup failed" in caplog.text

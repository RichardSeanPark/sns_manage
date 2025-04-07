import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl
import httpx
from bs4 import BeautifulSoup

# agents 임포트 시도
try:
    from agents import tool
except ImportError:
    # 대체 데코레이터 정의
    def tool(func):
        return func
    logger = logging.getLogger(__name__)
    logger.warning("Could not import 'agents' library. Using dummy 'tool' decorator.")

from app.utils.data_collection import parse_rss_feed # 방금 만든 유틸리티 함수 임포트
from app.models.collected_data import CollectedData # 임포트 경로 수정
from app.config import RSS_SOURCES, USER_AGENT # 설정에서 RSS 소스 목록, User-Agent 가져오기
from app.models.enums import SourceType, ProcessingStatus # SourceType, ProcessingStatus 추가
from datetime import datetime, timezone # datetime, timezone 추가

logger = logging.getLogger(__name__)

# --- Collect RSS Feeds Tool ---

class CollectRssInput(BaseModel):
    # 특정 URL 목록을 직접 지정하거나, 설정의 모든 소스를 대상으로 할 수 있도록 설계
    target_urls: Optional[List[HttpUrl]] = Field(default=None, description="수집할 RSS 피드 URL 목록. 지정하지 않으면 설정 파일(config.py)의 모든 RSS 소스를 대상으로 함.")

@tool
async def collect_rss_feeds_tool(input_data: CollectRssInput) -> List[CollectedData]:
    """
    지정된 RSS 피드 URL 목록 또는 설정된 모든 RSS 피드에서 최신 기사를 수집합니다.
    수집된 각 기사는 CollectedData 객체로 변환되어 리스트로 반환됩니다.
    """
    logger.info(f"Tool 'collect_rss_feeds_tool' called with input: {input_data}")
    all_collected_items: List[CollectedData] = []
    tasks = []

    source_map = {source["url"]: source.get("category", "Unknown") for source in RSS_SOURCES}

    urls_to_process: List[str] = []
    if input_data.target_urls:
        urls_to_process = [str(url) for url in input_data.target_urls]
        logger.info(f"Processing specified {len(urls_to_process)} RSS feed URLs.")
    else:
        urls_to_process = list(source_map.keys())
        logger.info(f"Processing all {len(urls_to_process)} configured RSS feed URLs.")

    for url in urls_to_process:
        category = source_map.get(url, "Unknown") # URL에 해당하는 카테고리 찾기
        # 각 URL 파싱 작업을 비동기 태스크로 생성
        tasks.append(parse_rss_feed(url, category=category))

    # 모든 파싱 태스크를 동시에 실행하고 결과 기다림
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 결과 처리
    for result in results:
        if isinstance(result, Exception):
            # 개별 피드 파싱 실패 로깅 (이미 parse_rss_feed 내부에서 로깅됨)
            logger.error(f"An error occurred during RSS feed parsing: {result}")
        elif isinstance(result, list):
            all_collected_items.extend(result) # 성공 결과 리스트에 추가

    logger.info(f"Total {len(all_collected_items)} items collected from RSS feeds.")
    return all_collected_items

# --- Crawl Webpage Tool ---

class CrawlInput(BaseModel):
    url: HttpUrl = Field(description="콘텐츠를 수집할 웹 페이지 URL")

# 주의: 웹 크롤링은 대상 웹사이트의 robots.txt 규칙을 준수해야 합니다.
#       또한, 웹사이트 구조 변경에 매우 취약합니다.
#       실제 운영 환경에서는 Playwright 같은 더 강력한 도구나
#       전문 크롤링 프레임워크(Scrapy 등) 사용을 고려해야 합니다.
@tool
async def crawl_webpage_tool(input_data: CrawlInput) -> Optional[CollectedData]:
    """
    주어진 URL의 웹 페이지에서 제목과 본문 콘텐츠를 추출하여 CollectedData 객체로 반환합니다.
    추출 실패 또는 오류 발생 시 None을 반환합니다.
    """
    url = str(input_data.url)
    logger.info(f"Tool 'crawl_webpage_tool' called for URL: {url}")

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            # 웹사이트 차단을 피하기 위해 User-Agent 설정
            headers = {'User-Agent': USER_AGENT}
            response = await client.get(url, headers=headers)
            response.raise_for_status() # HTTP 오류 발생 시 예외 발생

        # HTML 파싱
        soup = BeautifulSoup(response.text, 'lxml') # lxml 파서 사용

        # 제목 추출 (가장 기본적인 방식)
        title = soup.title.string if soup.title else url # 제목 없으면 URL 사용

        # 본문 추출 (매우 기본적인 방식 - 실제로는 더 정교한 선택자 필요)
        # <article>, <main>, 또는 주요 콘텐츠 div 등을 시도해볼 수 있음
        body_content = ""
        article_tag = soup.find('article')
        main_tag = soup.find('main')
        body_tag = soup.find('body')

        if article_tag:
            body_content = article_tag.get_text(separator='\n', strip=True)
        elif main_tag:
            body_content = main_tag.get_text(separator='\n', strip=True)
        elif body_tag:
            # body 전체는 너무 클 수 있으므로, 주요 단락(p)만 추출하는 등 개선 필요
            paragraphs = body_tag.find_all('p')
            body_content = '\n'.join([p.get_text(strip=True) for p in paragraphs])
        else:
            logger.warning(f"Could not extract main content from {url}")

        if not body_content:
             logger.warning(f"Extracted empty content from {url}")
             # 내용이 없으면 저장 가치가 낮으므로 None 반환 고려
             # return None

        # 현재 시간으로 collected_at 설정
        collected_at = datetime.now(timezone.utc)

        # CollectedData 객체 생성 (기본 정보만 채움)
        collected_item = CollectedData(
            source_url=url,
            source_type=SourceType.CRAWLING, # 소스 타입 CRAWLING으로 지정
            collected_at=collected_at,
            title=title.strip() if title else url,
            link=url, # 웹페이지의 경우 link는 source_url과 동일
            published_at=None, # 웹페이지에서 발행일 추출은 어려움
            summary=body_content[:500] + '...' if body_content else None, # 본문 앞부분을 요약으로 사용
            content=body_content,
            author=None, # 저자 추출 어려움
            categories=["Web"], # 기본 카테고리
            tags=[],
            processing_status=ProcessingStatus.RAW
        )
        logger.info(f"Successfully crawled and parsed content from: {url}")
        return collected_item

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred while crawling {url}: {e.response.status_code} - {e.response.reason_phrase}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Request error occurred while crawling {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error crawling or parsing webpage {url}: {e}", exc_info=True)
        return None

# TODO: 웹 크롤링 도구 (crawl_webpage_tool) 정의 필요

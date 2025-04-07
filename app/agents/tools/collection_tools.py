import asyncio
import logging
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl

from agents import tool
from app.utils.data_collection import parse_rss_feed # 방금 만든 유틸리티 함수 임포트
from app.models.pydantic_models import CollectedData
from app.config import RSS_SOURCES # 설정에서 RSS 소스 목록 가져오기 (카테고리 정보 활용)

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

# TODO: 웹 크롤링 도구 (crawl_webpage_tool) 정의 필요

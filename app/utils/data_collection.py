import logging
import feedparser
import time
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from dateutil import parser as date_parser

from app.config import USER_AGENT
from app.models.collected_data import CollectedData
from app.models.enums import SourceType, ProcessingStatus

logger = logging.getLogger(__name__)

def _parse_published_date(entry: feedparser.FeedParserDict) -> Optional[datetime]:
    """피드 항목의 발행일을 파싱하여 UTC datetime 객체로 변환합니다."""
    published_dt = None
    entry_link = entry.get('link', 'N/A')

    # 1. published_parsed (struct_time)
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        try:
            # time.mktime은 로컬 타임존을 사용하므로 UTC 변환 시 주의 필요
            # feedparser가 UTC로 파싱했다면 struct_time에서 직접 생성 가능
            # 여기서는 간단하게 fromtimestamp 사용 (로컬 타임존 의존성 가능성 있음)
            ts = time.mktime(entry.published_parsed)
            published_dt = datetime.fromtimestamp(ts, timezone.utc)
        except Exception as e:
            logger.debug(f"Could not parse 'published_parsed' for entry {entry_link} via mktime: {e}")
            try: # struct_time 직접 변환 시도
                 published_dt = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            except Exception as e_direct:
                 logger.debug(f"Could not parse 'published_parsed' directly for entry {entry_link}: {e_direct}")
                 published_dt = None


    # 2. published (string)
    if published_dt is None and hasattr(entry, 'published') and entry.published:
        published_str = entry.published
        try:
            published_dt = date_parser.parse(published_str)
            # 타임존 정보가 없으면 UTC로 가정, 있으면 UTC로 변환
            if published_dt.tzinfo is None or published_dt.tzinfo.utcoffset(published_dt) is None:
                published_dt = published_dt.replace(tzinfo=timezone.utc)
            else:
                published_dt = published_dt.astimezone(timezone.utc)
        except Exception as e:
            logger.debug(f"Could not parse 'published' string '{published_str}' for entry {entry_link}: {e}")
            published_dt = None

    # 3. updated_parsed (struct_time) - fallback
    if published_dt is None and hasattr(entry, 'updated_parsed') and entry.updated_parsed:
         try:
            ts = time.mktime(entry.updated_parsed)
            published_dt = datetime.fromtimestamp(ts, timezone.utc)
         except Exception as e:
             logger.debug(f"Could not parse 'updated_parsed' for entry {entry_link} via mktime: {e}")
             try:
                 published_dt = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
             except Exception as e_direct:
                 logger.debug(f"Could not parse 'updated_parsed' directly for entry {entry_link}: {e_direct}")

    return published_dt

async def parse_rss_feed(url: str, category: str = "Unknown") -> List[CollectedData]:
    """
    주어진 RSS 피드 URL에서 데이터를 파싱하여 CollectedData 객체 리스트를 반환합니다.
    네트워크 오류나 파싱 오류 발생 시 빈 리스트를 반환합니다.
    """
    collected_items: List[CollectedData] = []
    logger.info(f"Parsing RSS feed from: {url} (Category: {category})")

    try:
        # feedparser는 동기 라이브러리이므로 asyncio.to_thread 사용 고려 가능 (현재는 직접 호출)
        # TODO: 대규모 작업 시 비동기 HTTP 클라이언트와 XML 파서 조합 또는 to_thread 고려
        feed_data = feedparser.parse(url,
                                   agent=USER_AGENT,
                                   request_headers={'Accept': 'application/rss+xml, application/xml'})

        if feed_data.bozo:
            bozo_exception = feed_data.get("bozo_exception", Exception("Unknown parsing error"))
            logger.warning(f"Feed from {url} is ill-formed: {bozo_exception}")
            # bozo=1 이어도 일부 항목은 파싱될 수 있으므로 계속 진행

        if not feed_data.entries:
             logger.warning(f"No entries found in feed: {url}")
             return []

        logger.info(f"Found {len(feed_data.entries)} entries in feed: {url}")

        for entry in feed_data.entries:
            entry_link = entry.get('link', 'N/A')
            try:
                title = entry.get('title')
                link = entry.get('link')

                if not title or not link:
                    logger.warning(f"Skipping entry without title or link in feed {url}")
                    continue

                published_at = _parse_published_date(entry)
                summary = entry.get('summary')
                content = None
                # Content 추출 로직 (기존과 동일)
                if hasattr(entry, 'content') and entry.content:
                     if isinstance(entry.content, list) and entry.content:
                         content_item = entry.content[0]
                         if isinstance(content_item, dict):
                             content = content_item.get('value')
                     elif isinstance(entry.content, dict):
                         content = entry.content.get('value')
                     elif isinstance(entry.content, str):
                         content = entry.content
                if content is None and hasattr(entry, 'description'): # description을 fallback으로 사용
                     content = entry.description # 때로는 description이 더 나은 내용일 수 있음

                author = entry.get('author')
                tags = [tag.term for tag in entry.get('tags', []) if hasattr(tag, 'term')]

                collected_item = CollectedData(
                    source_url=url,
                    source_type=SourceType.RSS,
                    title=title,
                    link=link,
                    published_at=published_at,
                    summary=summary,
                    content=content,
                    author=author,
                    categories=[category], # 함수 인자로 받은 카테고리 사용
                    tags=tags,
                    processing_status=ProcessingStatus.RAW # 초기 상태
                )
                collected_items.append(collected_item)

            except Exception as e_entry:
                logger.error(f"Error processing entry from {url}, Link: {entry_link}. Error: {e_entry}", exc_info=True)
                # 개별 항목 오류는 무시하고 다음 항목 처리 계속

    except Exception as e_feed:
        logger.error(f"Failed to fetch or parse feed entirely: {url}. Error: {e_feed}", exc_info=True)
        return [] # 피드 자체 오류 시 빈 리스트 반환

    logger.info(f"Successfully parsed {len(collected_items)} items from {url}")
    return collected_items

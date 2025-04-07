import asyncio
import logging
import feedparser
import time
from datetime import datetime, timezone
import uuid
from typing import List, Tuple, Optional, Dict, Any
from dateutil import parser as date_parser

from app.config import RSS_SOURCES, USER_AGENT
from app.models.collected_data import CollectedData
from app.models.enums import SourceType, ProcessingStatus, MonitoringStatus
from app.repository.data_store import data_store
# 모니터링 저장소 임포트
from app.repository.monitoring_store import monitoring_store

logger = logging.getLogger(__name__)

def _parse_published_date(entry: feedparser.FeedParserDict) -> Optional[datetime]:
    """피드 항목의 발행일을 파싱하여 UTC datetime 객체로 변환합니다."""
    published_dt = None
    entry_link = entry.get('link', 'N/A')

    # 1. published_parsed (struct_time)
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        try:
            published_dt = datetime.fromtimestamp(time.mktime(entry.published_parsed), timezone.utc)
        except Exception as e:
            logger.debug(f"Could not parse 'published_parsed' for entry: {entry_link}, Error: {e}")
            published_dt = None

    # 2. published (string)
    if published_dt is None and hasattr(entry, 'published') and entry.published:
        published_str = entry.published
        try:
            published_dt = date_parser.parse(published_str)
            if published_dt.tzinfo is None:
                published_dt = published_dt.replace(tzinfo=timezone.utc)
            else:
                published_dt = published_dt.astimezone(timezone.utc)
        except Exception as e:
            logger.debug(f"Could not parse 'published' string '{published_str}' for entry: {entry_link}, Error: {e}")
            published_dt = None

    # 3. updated_parsed (struct_time) - fallback
    if published_dt is None and hasattr(entry, 'updated_parsed') and entry.updated_parsed:
         try:
            published_dt = datetime.fromtimestamp(time.mktime(entry.updated_parsed), timezone.utc)
         except Exception as e:
             logger.debug(f"Could not parse 'updated_parsed' for entry: {entry_link}, Error: {e}")

    return published_dt

async def collect_rss_feeds_task():
    """설정된 RSS 피드 소스에서 데이터를 수집하여 저장하고 모니터링 로그를 기록하는 태스크"""
    task_name = "rss_collection"
    log_id = monitoring_store.log_start(task_name)
    logger.info(f"Starting RSS feed collection task (Log ID: {log_id})...")

    total_entries_processed = 0
    total_entries_saved = 0
    total_entries_skipped = 0 # 중복 또는 오류로 저장되지 않은 항목 수
    failed_feeds_count = 0
    task_status = MonitoringStatus.STARTED
    task_error_message = None
    task_details: Dict[str, Any] = {"failed_feeds": []} # 실패한 피드 정보 저장

    try:
        for source_info in RSS_SOURCES:
            source_url = source_info["url"]
            category = source_info.get("category", "Unknown")
            logger.info(f"Fetching RSS feed from: {source_url} (Category: {category})")

            feed_entries_processed = 0
            feed_entries_saved = 0
            feed_entries_skipped_in_feed = 0 # 해당 피드 내에서 스킵된 항목 수
            feed_failed = False
            feed_error_msg = None

            try:
                feed_data = feedparser.parse(source_url,
                                           agent=USER_AGENT,
                                           request_headers={'Accept': 'application/rss+xml, application/xml'})

                if feed_data.bozo:
                    bozo_exception = feed_data.get("bozo_exception", Exception("Unknown parsing error"))
                    logger.warning(f"Feed from {source_url} is ill-formed: {bozo_exception}")
                    feed_error_msg = f"Feed ill-formed: {bozo_exception}"
                    feed_failed = True # bozo=1은 피드 실패로 간주

                if not feed_failed and not feed_data.entries:
                     logger.warning(f"No entries found in feed: {source_url}")
                     # 항목이 없는 것은 오류는 아님. 성공/실패 여부에 영향 주지 않음.
                     # 단, 로그에는 기록될 수 있음
                     continue

                logger.info(f"Found {len(feed_data.entries)} entries in feed: {source_url}")

                for entry in feed_data.entries:
                    total_entries_processed += 1
                    feed_entries_processed += 1
                    entry_link = entry.get('link', 'N/A')

                    try:
                        title = entry.get('title')
                        link = entry.get('link')

                        if not title or not link:
                            logger.warning(f"Skipping entry without title or link in feed {source_url}")
                            total_entries_skipped += 1
                            feed_entries_skipped_in_feed += 1
                            continue

                        published_at = _parse_published_date(entry)
                        summary = entry.get('summary')
                        content = None
                        if hasattr(entry, 'content') and entry.content:
                             if isinstance(entry.content, list) and entry.content:
                                 content_item = entry.content[0]
                                 if isinstance(content_item, dict):
                                     content = content_item.get('value')
                             elif isinstance(entry.content, dict):
                                 content = entry.content.get('value')
                             elif isinstance(entry.content, str):
                                 content = entry.content
                        if content is None and hasattr(entry, 'description'):
                             content = entry.description
                        author = entry.get('author')
                        tags = [tag.term for tag in entry.get('tags', []) if hasattr(tag, 'term')]

                        collected_item = CollectedData(
                            source_url=source_url,
                            source_type=SourceType.RSS,
                            title=title,
                            link=link,
                            published_at=published_at,
                            summary=summary,
                            content=content,
                            author=author,
                            categories=[category],
                            tags=tags,
                            processing_status=ProcessingStatus.RAW
                        )

                        saved_data = await data_store.save_data(collected_item, check_duplicates=True)

                        if saved_data:
                            total_entries_saved += 1
                            feed_entries_saved += 1
                            logger.debug(f"Saved entry: {title}")
                        else:
                            total_entries_skipped += 1
                            feed_entries_skipped_in_feed += 1
                            logger.debug(f"Skipped entry (e.g., duplicate): {title}")

                    except Exception as e_entry:
                        logger.error(f"Error processing entry from {source_url}, Link: {entry_link}. Error: {e_entry}", exc_info=True)
                        total_entries_skipped += 1
                        feed_entries_skipped_in_feed += 1
                        # 개별 항목 오류 발생 시, 피드 자체를 실패로 간주할지 정책 결정 필요
                        # 여기서는 개별 오류는 전체 태스크 실패로는 간주하지 않음

            except Exception as e_feed:
                logger.error(f"Failed to fetch or process feed entirely: {source_url}. Error: {e_feed}", exc_info=True)
                feed_failed = True
                feed_error_msg = str(e_feed)

            # 피드 처리 결과 로깅
            logger.info(f"Finished processing feed {source_url}. Saved: {feed_entries_saved}, Skipped: {feed_entries_skipped_in_feed}, Processed: {feed_entries_processed}, Failed: {feed_failed}")
            if feed_failed:
                failed_feeds_count += 1
                task_details["failed_feeds"].append({"url": source_url, "reason": feed_error_msg})

        # 전체 작업에 대한 최종 상태 결정
        if failed_feeds_count == len(RSS_SOURCES): # 모든 피드 실패
            task_status = MonitoringStatus.FAILED
            task_error_message = "All RSS feeds failed to process."
        elif failed_feeds_count > 0: # 일부 피드 실패
            task_status = MonitoringStatus.PARTIAL_SUCCESS
            task_error_message = f"{failed_feeds_count} RSS feeds failed."
        else: # 모든 피드 성공 (개별 항목 오류는 있을 수 있음)
            task_status = MonitoringStatus.SUCCESS

    except Exception as e_task:
        logger.error(f"Critical error during RSS collection task (Log ID: {log_id}). Error: {e_task}", exc_info=True)
        task_status = MonitoringStatus.FAILED
        task_error_message = f"Task-level error: {e_task}"

    finally:
        if log_id is not None:
            # 작업 종료 로깅
            monitoring_store.log_end(
                log_id=log_id,
                status=task_status,
                items_processed=total_entries_processed,
                items_succeeded=total_entries_saved,
                items_failed=total_entries_skipped, # 스킵/실패 합산
                error_message=task_error_message,
                details=task_details if task_details["failed_feeds"] else None # 실패 피드가 있을 때만 details 저장
            )
            logger.info(f"RSS feed collection task finished (Log ID: {log_id}). Status: {task_status.value}, Processed: {total_entries_processed}, Saved: {total_entries_saved}, Skipped/Failed Entries: {total_entries_skipped}, Failed Feeds: {failed_feeds_count}")
        else:
            logger.error("Could not log end of RSS collection task because log_id is None.")

    # 작업 결과 반환 (선택 사항)
    # return { ... } # 이전과 동일한 결과 구조 또는 상태 정보
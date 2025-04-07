import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import feedparser
import requests
from bs4 import BeautifulSoup
from pydantic import ValidationError

from app.config import DATA_DIR, RSS_SOURCES
from app.models.schemas import FeedItem, FeedSource

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# 임시 저장 경로
RAW_FEEDS_DIR = DATA_DIR / "raw_feeds"
os.makedirs(RAW_FEEDS_DIR, exist_ok=True)


class RSSCollector:
    """RSS 피드 수집 클래스"""
    
    def __init__(self, feed_sources: Optional[List[Dict]] = None, timeout: int = 30):
        """
        RSS 피드 수집기 초기화
        
        Args:
            feed_sources: RSS 피드 소스 목록. 지정하지 않으면 config.py의 RSS_SOURCES 사용
            timeout: RSS 피드 요청 타임아웃 (초)
        """
        self.feed_sources = feed_sources or RSS_SOURCES
        self.timeout = timeout
        logger.info(f"RSSCollector 초기화: {len(self.feed_sources)} 개의 피드 소스 로드")
    
    def fetch_all_feeds(self) -> List[FeedItem]:
        """
        모든 RSS 피드 소스에서 기사를 수집
        
        Returns:
            수집된 피드 아이템 목록
        """
        all_items = []
        
        for source in self.feed_sources:
            try:
                items = self.fetch_feed(source)
                all_items.extend(items)
                logger.info(f"피드 수집 완료: {source['name']}, {len(items)}개 항목 발견")
            except Exception as e:
                logger.error(f"피드 수집 실패: {source['name']} - {str(e)}")
        
        # 중복 제거
        unique_items = self._remove_duplicates(all_items)
        
        # 수집 결과 저장
        self._save_feeds(unique_items)
        
        logger.info(f"총 {len(all_items)}개 항목 수집, 중복 제거 후 {len(unique_items)}개 남음")
        return unique_items
    
    def fetch_feed(self, source: Dict) -> List[FeedItem]:
        """
        특정 RSS 피드 소스에서 기사를 수집
        
        Args:
            source: RSS 피드 소스 정보
            
        Returns:
            수집된 피드 아이템 목록
        """
        try:
            feed = feedparser.parse(source['url'], timeout=self.timeout)
            
            if feed.bozo == 1 and not feed.entries:
                logger.warning(f"피드 파싱 오류: {source['url']} - {feed.bozo_exception}")
                return []
            
            items = []
            for entry in feed.entries:
                try:
                    # 게시 날짜 파싱
                    published = self._parse_date(entry)
                    
                    # 콘텐츠 추출
                    content = self._extract_content(entry)
                    
                    # 태그 추출
                    tags = self._extract_tags(entry)
                    
                    # 아이템 ID 생성
                    item_id = str(uuid.uuid5(uuid.NAMESPACE_URL, entry.link))
                    
                    # FeedItem 객체 생성
                    item = FeedItem(
                        id=item_id,
                        title=entry.title,
                        description=entry.get('summary', ''),
                        content=content,
                        link=entry.link,
                        published=published,
                        updated=published,  # 대부분의 피드는 updated를 제공하지 않음
                        source_name=source['name'],
                        source_url=source['url'],
                        source_category=source['category'],
                        tags=tags
                    )
                    
                    items.append(item)
                except (ValidationError, KeyError, AttributeError) as e:
                    logger.warning(f"피드 항목 파싱 오류: {source['name']} - {str(e)}")
                    continue
            
            return items
        except Exception as e:
            logger.error(f"피드 요청 오류: {source['url']} - {str(e)}")
            return []
    
    def _parse_date(self, entry) -> datetime:
        """
        피드 엔트리에서 날짜 정보를 추출하여 datetime 객체로 변환
        
        Args:
            entry: feedparser 엔트리
            
        Returns:
            datetime 객체
        """
        for date_field in ['published_parsed', 'updated_parsed', 'created_parsed']:
            if hasattr(entry, date_field) and getattr(entry, date_field):
                time_struct = getattr(entry, date_field)
                return datetime.fromtimestamp(time.mktime(time_struct))
        
        # 날짜 정보가 없는 경우 현재 시간 반환
        return datetime.now()
    
    def _extract_content(self, entry) -> str:
        """
        피드 엔트리에서 본문 콘텐츠를 추출
        
        Args:
            entry: feedparser 엔트리
            
        Returns:
            추출된 콘텐츠 문자열
        """
        # content 필드가 있는 경우
        if hasattr(entry, 'content') and entry.content:
            for content in entry.content:
                if content.get('type') == 'text/html':
                    html_content = content.get('value', '')
                    return self._clean_html(html_content)
        
        # content 필드가 없지만 summary가 있는 경우
        if hasattr(entry, 'summary'):
            return self._clean_html(entry.summary)
        
        # 둘 다 없는 경우 빈 문자열 반환
        return ""
    
    def _clean_html(self, html_content: str) -> str:
        """
        HTML 문자열에서 태그를 제거하고 텍스트만 추출
        
        Args:
            html_content: HTML 문자열
            
        Returns:
            정제된 텍스트
        """
        if not html_content:
            return ""
        
        # BeautifulSoup으로 HTML 파싱
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 텍스트만 추출
        text = soup.get_text(separator=' ', strip=True)
        
        # 여러 공백을 하나로 치환
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _extract_tags(self, entry) -> List[str]:
        """
        피드 엔트리에서 태그를 추출
        
        Args:
            entry: feedparser 엔트리
            
        Returns:
            태그 목록
        """
        tags = []
        
        # 태그 필드가 있는 경우
        if hasattr(entry, 'tags'):
            for tag in entry.tags:
                tag_name = tag.get('term', '')
                if tag_name and tag_name not in tags:
                    tags.append(tag_name)
        
        # 카테고리 필드가 있는 경우
        if hasattr(entry, 'categories'):
            for category in entry.categories:
                if isinstance(category, tuple) and len(category) > 0:
                    category_name = category[0]
                    if category_name and category_name not in tags:
                        tags.append(category_name)
                elif isinstance(category, str) and category not in tags:
                    tags.append(category)
        
        return tags
    
    def _remove_duplicates(self, items: List[FeedItem]) -> List[FeedItem]:
        """
        URL 기반으로 중복 피드 아이템 제거
        
        Args:
            items: 피드 아이템 목록
            
        Returns:
            중복이 제거된 피드 아이템 목록
        """
        seen_urls = set()
        unique_items = []
        
        for item in items:
            url = str(item.link)
            if url not in seen_urls:
                seen_urls.add(url)
                unique_items.append(item)
        
        return unique_items
    
    def _save_feeds(self, items: List[FeedItem]):
        """
        수집된 피드 아이템을 JSON 파일로 저장
        
        Args:
            items: 저장할 피드 아이템 목록
        """
        if not items:
            return
        
        # 파일명 생성 (현재 시간 기준)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = RAW_FEEDS_DIR / f"feeds_{timestamp}.json"
        
        # JSON으로 변환하여 저장
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(
                [item.model_dump() for item in items],  # dict() 대신 model_dump() 사용
                f,
                ensure_ascii=False,
                indent=2,
                default=self._json_serializer
            )
        
        logger.info(f"피드 결과 저장 완료: {filename}")
    
    def _json_serializer(self, obj):
        """JSON 직렬화를 위한 도우미 함수"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        try:
            # 다양한 유형의 객체에 대해 문자열 변환 시도
            return str(obj)
        except:
            raise TypeError(f"Type {type(obj)} not serializable")


def collect_feeds() -> List[FeedItem]:
    """
    모든 RSS 피드를 수집하는 헬퍼 함수
    
    Returns:
        수집된 피드 아이템 목록
    """
    collector = RSSCollector()
    return collector.fetch_all_feeds()


if __name__ == "__main__":
    # 모듈 직접 실행 시 테스트
    collect_feeds()

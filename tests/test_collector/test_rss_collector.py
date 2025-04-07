import json
import os
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import feedparser

from app.collector.rss_collector import RSSCollector, collect_feeds
from app.models.schemas import FeedItem


class TestRSSCollector(unittest.TestCase):
    """RSS 피드 수집 모듈 테스트 클래스"""
    
    def setUp(self):
        """테스트 설정"""
        # 테스트용 피드 소스
        self.test_sources = [
            {
                "name": "Test Feed 1",
                "url": "https://example.com/feed1.xml",
                "category": "test"
            },
            {
                "name": "Test Feed 2",
                "url": "https://example.com/feed2.xml",
                "category": "test"
            }
        ]
        
        # 임시 수집기 생성
        self.collector = RSSCollector(feed_sources=self.test_sources)
    
    def test_clean_html(self):
        """HTML 정리 기능 테스트"""
        # 테스트용 HTML 내용
        html_content = "<div>Hello <b>World</b>! <script>alert('test');</script></div>"
        
        # HTML 정리 함수 실행
        cleaned_text = self.collector._clean_html(html_content)
        
        # 결과 검증 - 정확한 문자열 확인
        self.assertEqual(cleaned_text, "Hello World !")
        
        # 빈 HTML 테스트
        self.assertEqual(self.collector._clean_html(""), "")
        self.assertEqual(self.collector._clean_html(None), "")
    
    @patch('app.collector.rss_collector.RSSCollector.fetch_feed')
    @patch('app.collector.rss_collector.RSSCollector._save_feeds')
    def test_fetch_all_feeds(self, mock_save_feeds, mock_fetch_feed):
        """모든 피드 수집 기능 테스트"""
        # fetch_feed의 목업 결과 생성
        item1 = FeedItem(
            id="1",
            title="Article 1",
            description="Description 1",
            content="Content 1",
            link="https://example.com/article1",
            published=datetime.now(),
            source_name="Test Feed 1",
            source_url="https://example.com/feed1.xml",
            source_category="test",
            tags=["tag1", "tag2"]
        )
        
        item2 = FeedItem(
            id="2",
            title="Article 2",
            description="Description 2",
            content="Content 2",
            link="https://example.com/article2",
            published=datetime.now(),
            source_name="Test Feed 2",
            source_url="https://example.com/feed2.xml",
            source_category="test",
            tags=["tag2", "tag3"]
        )
        
        # 각 소스별로 반환할 아이템 설정
        mock_fetch_feed.side_effect = [[item1], [item2]]
        
        # _save_feeds 메서드가 아무 작업도 하지 않도록 설정
        mock_save_feeds.return_value = None
        
        # 모든 피드 수집 실행
        items = self.collector.fetch_all_feeds()
        
        # 결과 검증
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "Article 1")
        self.assertEqual(items[1].title, "Article 2")
        
        # fetch_feed가 각 소스에 대해 한 번씩 호출되었는지 확인
        self.assertEqual(mock_fetch_feed.call_count, 2)
    
    def test_remove_duplicates(self):
        """중복 제거 기능 테스트"""
        # 중복된 URL을 가진 아이템 생성
        item1 = FeedItem(
            id="1",
            title="Article 1",
            description="Description 1",
            content="Content 1",
            link="https://example.com/article1",
            published=datetime.now(),
            source_name="Test Feed 1",
            source_url="https://example.com/feed1.xml",
            source_category="test",
            tags=["tag1", "tag2"]
        )
        
        item2 = FeedItem(
            id="2",
            title="Article 2",
            description="Description 2",
            content="Content 2",
            link="https://example.com/article2",
            published=datetime.now(),
            source_name="Test Feed 2",
            source_url="https://example.com/feed2.xml",
            source_category="test",
            tags=["tag2", "tag3"]
        )
        
        item3 = FeedItem(
            id="3",
            title="Article 1 (Duplicate)",
            description="Duplicate Description",
            content="Duplicate Content",
            link="https://example.com/article1",  # 중복된 URL
            published=datetime.now(),
            source_name="Test Feed 3",
            source_url="https://example.com/feed3.xml",
            source_category="test",
            tags=["tag1", "tag4"]
        )
        
        # 중복 제거 실행
        items = [item1, item2, item3]
        unique_items = self.collector._remove_duplicates(items)
        
        # 결과 검증
        self.assertEqual(len(unique_items), 2)
        
        # URL이 중복된 item1과 item3 중 하나만 남아 있어야 함
        urls = [str(item.link) for item in unique_items]
        self.assertIn("https://example.com/article1", urls)
        self.assertIn("https://example.com/article2", urls)
        
        # 중복 제거 시 처음 나온 항목이 보존되어야 함
        titles = [item.title for item in unique_items]
        self.assertIn("Article 1", titles)
        self.assertNotIn("Article 1 (Duplicate)", titles)
    
    @patch('app.collector.rss_collector.open')
    @patch('app.collector.rss_collector.json.dump')
    def test_save_feeds(self, mock_json_dump, mock_open):
        """피드 저장 기능 테스트"""
        # 저장할 샘플 아이템 생성
        item = FeedItem(
            id="1",
            title="Article 1",
            description="Description 1",
            content="Content 1",
            link="https://example.com/article1",
            published=datetime.now(),
            source_name="Test Feed 1",
            source_url="https://example.com/feed1.xml",
            source_category="test",
            tags=["tag1", "tag2"]
        )
        
        # 피드 저장 실행
        self.collector._save_feeds([item])
        
        # 파일 열기가 호출되었는지 확인
        mock_open.assert_called_once()
        
        # json.dump가 호출되었는지 확인
        mock_json_dump.assert_called_once()


if __name__ == '__main__':
    unittest.main() 
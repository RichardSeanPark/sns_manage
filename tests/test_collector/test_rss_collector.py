import json
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, mock_open, call
import time
import logging
from pathlib import Path
import tempfile

import feedparser
from pydantic import ValidationError

# 모듈 경로 설정을 위해 필요할 수 있음 (프로젝트 구조에 따라)
# import sys
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app.collector.rss_collector import RSSCollector
from app.models.schemas import FeedItem
# 실제 설정 파일을 로드하기 위해 필요
from app.config import RSS_SOURCES, DATA_DIR 

# 테스트 중 로그 출력을 보기 위해 설정 (선택적)
# logging.basicConfig(level=logging.DEBUG)

class TestRSSCollector(unittest.TestCase):
    """RSS 피드 수집 모듈 테스트 클래스"""

    def setUp(self):
        """테스트 설정"""
        self.test_sources = [
            {
                "name": "Test Feed 1",
                "url": "https://example.com/feed1.xml",
                "category": "Technology",
                "priority": 1, # 예시 우선순위
                "update_interval": 12 # 예시 업데이트 주기
            },
            {
                "name": "Test Feed 2",
                "url": "https://example.com/feed2.xml",
                "category": "AI Research",
                "priority": 2,
                "update_interval": 24
            }
        ]
        # timeout 추가
        self.collector = RSSCollector(feed_sources=self.test_sources, timeout=10)
        # 임시 디렉토리 생성 for _save_feeds test
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_data_dir = Path(self.temp_dir.name)
        # DATA_DIR 패치 for _save_feeds test
        self.data_dir_patch = patch('app.collector.rss_collector.DATA_DIR', self.test_data_dir)
        # rss_collector 모듈 내의 RAW_FEEDS_DIR도 패치해야 할 수 있음
        self.raw_feeds_dir_patch = patch('app.collector.rss_collector.RAW_FEEDS_DIR', self.test_data_dir / "raw_feeds")
        self.data_dir_patch.start()
        self.raw_feeds_dir_patch.start()
        # RAW_FEEDS_DIR이 실제로 생성되도록 보장
        os.makedirs(self.test_data_dir / "raw_feeds", exist_ok=True)

    def tearDown(self):
        """테스트 종료 후 정리"""
        self.temp_dir.cleanup()
        self.data_dir_patch.stop()
        self.raw_feeds_dir_patch.stop()

    # --- TC-001: _clean_html --- 
    def test_clean_html(self):
        """TC-001: HTML 정리 기능 테스트"""
        html_content = "  <div> Hello  <b>World </b> ! <script>alert('test');</script>Extra space.</div>  "
        # Expected: script 제거, 태그 제거, 앞뒤/중복 공백 제거, 구두점 앞 공백 제거
        cleaned_text = self.collector._clean_html(html_content)
        self.assertEqual(cleaned_text, "Hello World! Extra space.")
        self.assertEqual(self.collector._clean_html(""), "")
        self.assertEqual(self.collector._clean_html(None), "")

    # --- TC-003: _remove_duplicates --- 
    def test_remove_duplicates(self):
        """TC-003: 중복 제거 기능 테스트"""
        now = datetime.now()
        # Use valid URLs for source_url
        item1 = FeedItem(id="1", title="A1", link="http://a.com/1", published=now, source_name="S1", source_url="http://example.com/s1.xml", source_category="C1")
        item2 = FeedItem(id="2", title="A2", link="http://a.com/2", published=now, source_name="S2", source_url="http://example.com/s2.xml", source_category="C2")
        item3 = FeedItem(id="3", title="A3", link="http://a.com/1", published=now, source_name="S3", source_url="http://example.com/s3.xml", source_category="C1") # Duplicate URL
        items = [item1, item2, item3]
        unique_items = self.collector._remove_duplicates(items)
        self.assertEqual(len(unique_items), 2)
        self.assertEqual(unique_items[0].id, "1")
        self.assertEqual(unique_items[1].id, "2")

    # --- TC-004: _save_feeds (modified file pattern) --- 
    def test_save_feeds(self):
        """TC-004: 피드 저장 기능 테스트 (실제 파일)"""
        now = datetime.now()
        item = FeedItem(
            id="t1", 
            title="Test Title", 
            description="Test Desc",
            content="Test Content",
            link="http://test.com/article", 
            published=now, 
            source_name="Test Source", 
            source_url="http://feeds.example.com/test.xml", 
            source_category="Test Cat",
            tags=["t1", "t2"]
        )
        items = [item]
        
        self.collector._save_feeds(items)

        expected_dir = self.test_data_dir / "raw_feeds"
        # Correct the file search pattern to match the actual filename format
        saved_files = list(expected_dir.glob("feeds_*.json")) 
        self.assertEqual(len(saved_files), 1, f"Expected 1 file matching 'feeds_*.json', found {len(saved_files)} in {expected_dir}")
        file_path = saved_files[0]
        
        # Verify file content (remains the same)
        with open(file_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        self.assertEqual(len(saved_data), 1)
        saved_item = saved_data[0]
        self.assertEqual(saved_item['id'], item.id)
        self.assertEqual(saved_item['title'], item.title)
        self.assertEqual(saved_item['link'], str(item.link))
        self.assertEqual(datetime.fromisoformat(saved_item['published']), item.published)
        self.assertEqual(saved_item['source_name'], item.source_name)
        self.assertEqual(saved_item['source_url'], str(item.source_url)) 
        self.assertEqual(saved_item['tags'], item.tags)
        try:
            FeedItem(**saved_item) # Load back check
        except ValidationError as e:
            self.fail(f"Saved JSON data does not match FeedItem schema: {e}")

    # --- 신규 및 보강 테스트 --- 

    @patch('app.collector.rss_collector.RSSCollector.fetch_feed')
    @patch('app.collector.rss_collector.RSSCollector._remove_duplicates')
    @patch('app.collector.rss_collector.RSSCollector._save_feeds')
    def test_fetch_all_feeds(self, mock_save, mock_remove, mock_fetch):
        """TC-002: 모든 피드 수집 기능 테스트"""
        # Simulate FeedItem objects (can be MagicMock or real FeedItem)
        item1 = MagicMock(spec=FeedItem, link="http://a.com/1") 
        item2 = MagicMock(spec=FeedItem, link="http://a.com/2")
        item3 = MagicMock(spec=FeedItem, link="http://a.com/3")
        # Ensure side_effect provides lists of items for each call to fetch_feed
        mock_fetch.side_effect = [[item1], [item2, item3]]
        # Simulate remove_duplicates returning a filtered list
        mock_remove.return_value = [item1, item2] # Assuming item3 was duplicate or filtered

        # Call the method under test
        result = self.collector.fetch_all_feeds()

        # Assertions
        self.assertEqual(mock_fetch.call_count, len(self.test_sources))
        # Check calls were made with the correct source dictionaries
        mock_fetch.assert_any_call(self.test_sources[0])
        mock_fetch.assert_any_call(self.test_sources[1])
        # Check _remove_duplicates was called with the combined list from fetch_feed
        mock_remove.assert_called_once_with([item1, item2, item3])
        # Check _save_feeds was called with the result from _remove_duplicates
        mock_save.assert_called_once_with([item1, item2])
        # Check the final returned value
        self.assertEqual(result, [item1, item2])

    def test_load_rss_sources(self):
        """TC-005: 피드 소스 로딩 및 검증 테스트"""
        # Uses RSS_SOURCES imported from app.config
        default_collector = RSSCollector() # Initialize without specific sources
        self.assertIsNotNone(default_collector.feed_sources)
        self.assertGreater(len(default_collector.feed_sources), 0)
        # Check against the imported RSS_SOURCES list
        self.assertEqual(default_collector.feed_sources, RSS_SOURCES)
        
        # Validate structure of each source in the actual config
        for source in default_collector.feed_sources:
            self.assertIsInstance(source, dict)
            self.assertIn('name', source)
            self.assertIsInstance(source['name'], str)
            self.assertIn('url', source)
            self.assertIsInstance(source['url'], str)
            self.assertTrue(source['url'].startswith('http'), f"URL invalid for {source['name']}: {source['url']}")
            self.assertIn('category', source)
            self.assertIsInstance(source['category'], str)
            # Add checks for other mandatory keys if defined (e.g., priority, update_interval)
            # self.assertIn('priority', source)
            # self.assertIsInstance(source['priority'], int)
            # self.assertIn('update_interval', source)
            # self.assertIsInstance(source['update_interval'], int)

    @patch('app.collector.rss_collector.feedparser.parse')
    def test_fetch_feed_invalid_url_or_error(self, mock_parse):
        """TC-006, TC-014: 잘못된 URL 또는 요청 오류 처리 테스트"""
        source = self.test_sources[0]
        
        # Case 1: Network error (simulated by feedparser raising an exception)
        # feedparser itself might raise socket.gaierror or similar for bad URLs before timeout
        # or requests.exceptions.RequestException if it uses requests internally (needs confirmation)
        # Let's simulate a generic Exception during parse
        mock_parse.side_effect = Exception("Simulated network/parse error")
        # Check if ERROR log is generated
        with self.assertLogs('app.collector.rss_collector', level='ERROR') as cm:
            items = self.collector.fetch_feed(source)
        self.assertEqual(items, [])
        self.assertTrue(any("Simulated network/parse error" in log for log in cm.output))
        # Ensure the mock was called with the correct URL
        mock_parse.assert_called_with(source['url'], timeout=self.collector.timeout)
        
        # Case 2: Timeout error (simulated by feedparser raising TimeoutError)
        mock_parse.reset_mock() # Reset call count and side effect
        mock_parse.side_effect = TimeoutError("Request timed out")
        with self.assertLogs('app.collector.rss_collector', level='ERROR') as cm:
             items = self.collector.fetch_feed(source)
        self.assertEqual(items, [])
        self.assertTrue(any("timed out" in log for log in cm.output))
        # Ensure the mock was called again
        mock_parse.assert_called_with(source['url'], timeout=self.collector.timeout)

    @patch('app.collector.rss_collector.feedparser.parse')
    def test_fetch_feed_parse_error(self, mock_parse):
        """TC-010: 단일 피드 수집 (파싱 오류) 테스트"""
        source = self.test_sources[0]
        # Simulate parse error (bozo=1, no entries) using feedparser structure
        mock_error_feed = feedparser.FeedParserDict()
        mock_error_feed.bozo = 1
        mock_error_feed.bozo_exception = feedparser.CharacterEncodingOverride("Simulated encoding issue")
        mock_error_feed.entries = []
        # Set the return value specifically for this test
        mock_parse.return_value = mock_error_feed
        
        # Check for WARNING log in this case based on current code
        with self.assertLogs('app.collector.rss_collector', level='WARNING') as cm:
            items = self.collector.fetch_feed(source)
        self.assertEqual(items, [])
        self.assertTrue(any("Simulated encoding issue" in log for log in cm.output))
        # Ensure the mock was called
        mock_parse.assert_called_once_with(source['url'], timeout=self.collector.timeout)

    @patch('app.collector.rss_collector.feedparser.parse')
    def test_fetch_feed_empty(self, mock_parse):
        """TC-009: 단일 피드 수집 (빈 피드) 테스트"""
        source = self.test_sources[0]
        # Simulate empty feed (bozo=0, no entries)
        mock_empty_feed = feedparser.FeedParserDict()
        mock_empty_feed.bozo = 0
        mock_empty_feed.entries = []
        # Set the return value specifically for this test
        mock_parse.return_value = mock_empty_feed
        
        items = self.collector.fetch_feed(source)
        self.assertEqual(items, [])
        # Ensure no error/warning logs in this case
        # (Optional: check logs are clean if necessary)
        # Ensure the mock was called
        mock_parse.assert_called_once_with(source['url'], timeout=self.collector.timeout)

    @patch('app.collector.rss_collector.feedparser.parse')
    def test_fetch_feed_success_and_category(self, mock_parse):
        """TC-008, TC-007: 단일 피드 수집 성공 및 카테고리 할당 테스트"""
        source = self.test_sources[0] 
        source_b = self.test_sources[1]
        
        now_struct = time.gmtime()
        now_dt = datetime.fromtimestamp(time.mktime(now_struct))
        mock_entry1 = feedparser.FeedParserDict({
            'title': "Title 1",
            'link': "http://example.com/1", # Keep as string for mock
            'summary': "Summary 1",
            'published_parsed': now_struct, 
            'tags': [feedparser.FeedParserDict({'term': 'tagA'})]
        })
        mock_entry2 = feedparser.FeedParserDict({
            'title': "Title 2",
            'link': "http://example.com/2", # Keep as string for mock
            'summary': "Summary 2",
            'updated_parsed': now_struct,
            'categories': [['catB']]
        })

        mock_feed = feedparser.FeedParserDict()
        mock_feed.bozo = 0
        mock_feed.entries = [mock_entry1, mock_entry2]
        mock_parse.return_value = mock_feed
        
        items = self.collector.fetch_feed(source)
        
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].title, "Title 1")
        self.assertEqual(items[1].title, "Title 2")
        # Compare link by converting FeedItem.link (HttpUrl) to string
        self.assertEqual(str(items[0].link), "http://example.com/1")
        self.assertEqual(str(items[1].link), "http://example.com/2")
        self.assertEqual(items[0].published, now_dt)
        self.assertEqual(items[1].published, now_dt)
        self.assertEqual(items[0].source_category, "Technology")
        self.assertEqual(items[1].source_category, "Technology")
        self.assertEqual(items[0].source_name, source['name'])
        # Compare source_url by converting to string
        self.assertEqual(str(items[0].source_url), source['url'])
        self.assertIn('tagA', items[0].tags)
        self.assertIn('catB', items[1].tags)
        mock_parse.assert_called_once_with(source['url'], timeout=self.collector.timeout)

        mock_parse.reset_mock()
        items_b = self.collector.fetch_feed(source_b)
        self.assertEqual(len(items_b), 2)
        self.assertEqual(items_b[0].source_category, "AI Research")
        self.assertEqual(items_b[1].source_category, "AI Research")
        mock_parse.assert_called_once_with(source_b['url'], timeout=self.collector.timeout)

    def test_parse_date(self):
        """TC-011: 날짜 파싱 테스트"""
        # Create mock entries with different date fields
        # Note: time.mktime can be platform dependent or affected by timezone.
        # Using fixed datetime objects and converting to struct_time is safer.
        dt_pub = datetime(2023, 3, 15, 10, 0, 0)
        dt_upd = datetime(2023, 3, 16, 11, 30, 0)
        dt_cre = datetime(2023, 3, 17, 12, 45, 0)
        st_pub = dt_pub.timetuple()
        st_upd = dt_upd.timetuple()
        st_cre = dt_cre.timetuple()

        entry_published = feedparser.FeedParserDict({'published_parsed': st_pub})
        entry_updated = feedparser.FeedParserDict({'updated_parsed': st_upd}) # No published_parsed
        # Test fallback: updated_parsed missing, check created_parsed
        entry_created = feedparser.FeedParserDict({'created_parsed': st_cre}) # No published or updated
        entry_none = feedparser.FeedParserDict({}) # No date fields
        entry_invalid = feedparser.FeedParserDict({'published_parsed': None}) # Field exists but is None

        parsed_dt1 = self.collector._parse_date(entry_published)
        parsed_dt2 = self.collector._parse_date(entry_updated)
        parsed_dt3 = self.collector._parse_date(entry_created)
        parsed_dt_none = self.collector._parse_date(entry_none)
        parsed_dt_invalid = self.collector._parse_date(entry_invalid)
        
        self.assertEqual(parsed_dt1, dt_pub)
        self.assertEqual(parsed_dt2, dt_upd)
        self.assertEqual(parsed_dt3, dt_cre)
        # Check if fallback to current time is within a reasonable delta (e.g., 5 seconds)
        self.assertAlmostEqual(parsed_dt_none, datetime.now(), delta=timedelta(seconds=5))
        self.assertAlmostEqual(parsed_dt_invalid, datetime.now(), delta=timedelta(seconds=5))

    def test_extract_content(self):
        """TC-012: 콘텐츠 추출 및 정리 테스트"""
        # Case 1: Has HTML content in entry.content list
        mock_content_html = feedparser.FeedParserDict({
            'type': 'text/html', 
            'value': ' <p> Test <b>content</b> here. </p> '
        })
        mock_content_text = feedparser.FeedParserDict({
             'type': 'text/plain', 
             'value': ' Plain text content '
         })
        # Entry with both html and text content (html should be preferred if type is text/html)
        entry_content_html = feedparser.FeedParserDict({
            'content': [mock_content_text, mock_content_html], # Order matters if logic checks first
            'summary': 'Should ignore summary'
        })
        content1 = self.collector._extract_content(entry_content_html)
        self.assertEqual(content1, "Test content here.")

        # Case 2: Has only summary (HTML inside summary)
        entry_summary = feedparser.FeedParserDict({
            'summary': ' <div> Simple <i>summary</i>. </div> '
        })
        content2 = self.collector._extract_content(entry_summary)
        self.assertEqual(content2, "Simple summary.")
        
        # Case 3: No content or summary
        entry_none = feedparser.FeedParserDict({})
        content3 = self.collector._extract_content(entry_none)
        self.assertEqual(content3, "")
        
        # Case 4: Content field exists but is empty or has no value
        entry_empty_content = feedparser.FeedParserDict({'content': []})
        content4 = self.collector._extract_content(entry_empty_content)
        self.assertEqual(content4, "")
        mock_content_no_value = feedparser.FeedParserDict({'type': 'text/html'})
        entry_no_value = feedparser.FeedParserDict({'content': [mock_content_no_value]})
        content5 = self.collector._extract_content(entry_no_value)
        self.assertEqual(content5, "")

    def test_extract_tags(self):
        """TC-013: 태그 추출 테스트"""
        # Case 1: Has tags attribute (list of dicts with 'term')
        entry_tags = feedparser.FeedParserDict({
            'tags': [feedparser.FeedParserDict({'term': 'AI'}), 
                     feedparser.FeedParserDict({'term': 'ML'}), 
                     feedparser.FeedParserDict({'term': 'AI'})] # Duplicate tag
        })
        tags1 = self.collector._extract_tags(entry_tags)
        self.assertCountEqual(tags1, ['AI', 'ML']) # Check elements regardless of order, duplicates removed
        
        # Case 2: Has categories attribute (list of lists/tuples)
        entry_cats_tuple = feedparser.FeedParserDict({
            'categories': [['Research'], ['NLP']]
        })
        tags2 = self.collector._extract_tags(entry_cats_tuple)
        self.assertCountEqual(tags2, ['Research', 'NLP'])
        
        # Case 3: Has categories attribute (list of strings) - less common but possible
        # Note: feedparser usually returns list of lists for categories
        entry_cats_str = feedparser.FeedParserDict({
             'categories': ['News', 'Tech', 'News'] # Duplicate category
        })
        # Depending on the exact parsing logic in _extract_tags for string lists:
        # Assuming it handles simple strings directly:
        tags3 = self.collector._extract_tags(entry_cats_str)
        self.assertCountEqual(tags3, ['News', 'Tech'])
        
        # Case 4: Has both tags and categories
        entry_both = feedparser.FeedParserDict({
            'tags': [feedparser.FeedParserDict({'term': 'Python'})], 
            'categories': [['Programming'], ['Python']] # Duplicate via category
        })
        tags4 = self.collector._extract_tags(entry_both)
        self.assertCountEqual(tags4, ['Python', 'Programming'])
        
        # Case 5: No tags or categories
        entry_none = feedparser.FeedParserDict({})
        tags5 = self.collector._extract_tags(entry_none)
        self.assertEqual(tags5, [])
        
        # Case 6: Empty tag term or category
        entry_empty_term = feedparser.FeedParserDict({
            'tags': [feedparser.FeedParserDict({'term': ''}), feedparser.FeedParserDict({'term': 'Valid'})]
        })
        tags6 = self.collector._extract_tags(entry_empty_term)
        self.assertCountEqual(tags6, ['Valid'])

if __name__ == '__main__':
    unittest.main() 
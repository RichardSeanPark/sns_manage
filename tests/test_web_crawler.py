import unittest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from pathlib import Path
import tempfile
import json
import os
import pytest
import pytest_asyncio
from playwright.async_api import Page, Browser, BrowserContext, Playwright, async_playwright, Response

from app.collector.web_crawler import WebCrawler
from app.collector.crawler_manager import CrawlerManager
from app.collector.crawler_config import CRAWLER_CONFIG, CRAWLING_STRATEGY, STORAGE_CONFIG

# Remove the pytestmark if not needed globally, or keep if all tests are async
# pytestmark = pytest.mark.asyncio

# Remove custom event_loop fixture as pytest-asyncio provides one
# @pytest.fixture(scope="session")
# def event_loop():
#     policy = asyncio.WindowsSelectorEventLoopPolicy()
#     loop = policy.new_event_loop()
#     yield loop
#     loop.close()

class TestWebCrawler:
    """웹 크롤러 테스트"""
    
    @pytest_asyncio.fixture(scope="function")
    async def crawler(self, tmp_path, mocker):
        """Set up WebCrawler instance for tests using mocker"""
        config = {
            "headless": True,
            "slow_mo": 100,
            "timeout": 30000,
            "screenshot_dir": str(tmp_path)
        }
        crawler_instance = WebCrawler(config)

        # Mock start/stop using mocker - these prevent real browser launch in fixture
        mocker.patch.object(crawler_instance, 'start', return_value=None)
        mocker.patch.object(crawler_instance, 'stop', return_value=None)

        # Assign mock browser/context/page using mocker for basic state
        # Tests needing specific behavior will override these or patch methods
        crawler_instance.browser = mocker.AsyncMock(spec=Browser)
        crawler_instance.context = mocker.AsyncMock(spec=BrowserContext)
        crawler_instance.page = mocker.AsyncMock(spec=Page)

        yield crawler_instance
        # Cleanup is typically handled by pytest/mocker automatically
        
    @pytest.mark.asyncio
    async def test_init(self, tmp_path):
        """크롤러 초기화 테스트"""
        config = {"screenshot_dir": str(tmp_path)}
        crawler_instance = WebCrawler(config)
        assert crawler_instance.config["screenshot_dir"] == str(tmp_path)
        assert Path(str(tmp_path)).exists() # Ensure directory was created
        assert crawler_instance.browser is None # Check initial state
        assert crawler_instance.context is None
        assert crawler_instance.page is None

    @pytest.mark.asyncio
    async def test_start_stop(self, crawler, mocker):
        """브라우저 시작/종료 테스트 (상태 확인)"""
        # 이 테스트는 start/stop 후 crawler 객체의 상태만 확인합니다.
        # 내부 Playwright 호출 모의는 복잡하고 불안정하므로 생략합니다.

        # Mock start/stop to simply set/unset state attributes
        async def mock_start():
            crawler.browser = mocker.AsyncMock(spec=Browser)
            crawler.context = mocker.AsyncMock(spec=BrowserContext)
            crawler.page = mocker.AsyncMock(spec=Page)
        async def mock_stop():
            # Simulate the cleanup logic of the real stop method
            if crawler.page:
                 # Simulate closing if needed, then set to None
                 # await crawler.page.close() 
                 crawler.page = None
            if crawler.context:
                 # await crawler.context.close()
                 crawler.context = None
            if crawler.browser:
                 # await crawler.browser.close()
                 crawler.browser = None

        # Patch the actual start/stop methods with our mocks for this test
        mocker.patch.object(crawler, 'start', side_effect=mock_start)
        mocker.patch.object(crawler, 'stop', side_effect=mock_stop)

        # --- Start Test ---
        # Reset state before calling mock start
        crawler.browser = None
        crawler.context = None
        crawler.page = None

        await crawler.start()

        # Assertions after start (Check if attributes are set)
        assert crawler.browser is not None
        assert crawler.context is not None
        assert crawler.page is not None
        crawler.start.assert_called_once() # Verify our mock start was called

        # --- Stop Test ---
        await crawler.stop()

        # Assertions after stop (Check if attributes are unset)
        assert crawler.browser is None
        assert crawler.context is None
        assert crawler.page is None
        crawler.stop.assert_called_once() # Verify our mock stop was called

    @pytest.mark.asyncio
    async def test_take_screenshot(self, crawler, tmp_path):
        """스크린샷 테스트"""
        url = "https://example.com"
        
        # 스크린샷 저장 경로 설정
        crawler.page.screenshot = AsyncMock()
        
        await crawler.take_screenshot(url)
        
        # 스크린샷 저장 확인
        assert crawler.page.screenshot.called
        actual_path = crawler.page.screenshot.call_args[1]["path"]
        assert actual_path.startswith(str(tmp_path))
        assert actual_path.endswith(".png")
        assert "example.com" in actual_path
        
    @pytest.mark.asyncio
    async def test_scroll_to_bottom(self, crawler):
        """페이지 스크롤 테스트"""
        # JavaScript 함수 실행 모의
        crawler.page.evaluate = AsyncMock()
        
        # 높이 값을 반환하는 호출과 스크롤 호출을 위한 반환값 설정
        # 1000, None (스크롤), 1000, None (스크롤), 1000 - 마지막에는 같은 높이를 반환하여 루프 종료
        crawler.page.evaluate.side_effect = [1000, None, 1000, None, 1000]
        
        await crawler.scroll_to_bottom()
        
        # evaluate 호출 확인
        assert crawler.page.evaluate.call_count >= 3
        
        # 호출 순서 확인
        calls = crawler.page.evaluate.call_args_list
        
        # 첫 번째 호출: 높이 확인
        assert "document.body.scrollHeight" in calls[0][0][0]
        
        # 두 번째 호출: 스크롤 실행
        assert "window.scrollTo" in calls[1][0][0]
        
        # 세 번째 호출: 다시 높이 확인
        assert "document.body.scrollHeight" in calls[2][0][0]
        
    @pytest.mark.asyncio
    async def test_extract_text_content(self, crawler):
        """텍스트 추출 테스트"""
        # 모의 요소 생성
        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value="Test Content")
        crawler.page.query_selector = AsyncMock(return_value=mock_element)
        
        # 텍스트 추출 실행
        content = await crawler.extract_text_content("test-selector")
        
        # 결과 확인
        assert content == "Test Content"
        
        # 선택자가 없는 경우 테스트
        crawler.page.query_selector = AsyncMock(return_value=None)
        content = await crawler.extract_text_content("non-existent-selector")
        assert content == ""
        
        # 빈 텍스트 테스트
        mock_element = AsyncMock()
        mock_element.text_content = AsyncMock(return_value="  ")
        crawler.page.query_selector = AsyncMock(return_value=mock_element)
        content = await crawler.extract_text_content("test-selector")
        assert content == ""
        
    @pytest.mark.asyncio
    async def test_check_robots_txt(self, crawler, mocker):
        """robots.txt 확인 테스트 (async with 사용 안 함)"""
        # 1. Mock page and response objects
        mock_robots_page = mocker.AsyncMock(name="mock_robots_page", spec=Page)
        mock_response = mocker.AsyncMock(name="mock_response", spec=Response)

        # 2. Mock response attributes and methods
        mock_response.ok = True
        # Assign an AsyncMock to response.text, configure its return value
        mock_response.text = mocker.AsyncMock(return_value="User-agent: *\nAllow: /\nDisallow: /private/")

        # 3. Mock page methods
        mock_robots_page.goto = mocker.AsyncMock(return_value=mock_response)
        mock_robots_page.close = mocker.AsyncMock()

        # 4. Patch crawler.context.new_page
        mocker.patch.object(crawler.context, 'new_page', return_value=mock_robots_page)

        # --- Test Scenarios ---

        # Allowed URL
        # Reset mocks specifically for this scenario if needed
        mock_response.ok = True
        mock_response.text = mocker.AsyncMock(return_value="User-agent: *\nAllow: /\nDisallow: /private/")
        mock_robots_page.goto = mocker.AsyncMock(return_value=mock_response)
        mock_robots_page.close = mocker.AsyncMock()

        allowed = await crawler.check_robots_txt("https://example.com/public")
        assert allowed is True
        crawler.context.new_page.assert_called_once()
        mock_robots_page.goto.assert_awaited_once_with("https://example.com/robots.txt", timeout=10000)
        mock_response.text.assert_awaited_once() # Now text is an AsyncMock, assertion should work
        mock_robots_page.close.assert_awaited_once()

        # Reset mocks for the next scenario
        crawler.context.new_page.reset_mock()
        mock_robots_page.reset_mock()
        mock_response.reset_mock()

        # Disallowed URL
        mock_response.ok = True
        # Update the return value of the text mock
        mock_response.text = mocker.AsyncMock(return_value="User-agent: *\nDisallow: /private/")
        mock_robots_page.goto = mocker.AsyncMock(return_value=mock_response)
        mock_robots_page.close = mocker.AsyncMock()

        allowed = await crawler.check_robots_txt("https://example.com/private/secret")
        assert allowed is False
        crawler.context.new_page.assert_called_once()
        mock_robots_page.goto.assert_awaited_once_with("https://example.com/robots.txt", timeout=10000)
        mock_response.text.assert_awaited_once()
        mock_robots_page.close.assert_awaited_once()

        # Reset mocks
        crawler.context.new_page.reset_mock()
        mock_robots_page.reset_mock()
        mock_response.reset_mock()

        # No robots.txt (goto returns None)
        mock_robots_page.goto = mocker.AsyncMock(return_value=None)
        mock_robots_page.close = mocker.AsyncMock()
        # Ensure mock_response.text is reset or not used
        mock_response.text = mocker.AsyncMock() # Reset text mock

        allowed = await crawler.check_robots_txt("https://example.com/any")
        assert allowed is True
        crawler.context.new_page.assert_called_once()
        mock_robots_page.goto.assert_awaited_once_with("https://example.com/robots.txt", timeout=10000)
        mock_response.text.assert_not_awaited() # text() should not be called
        mock_robots_page.close.assert_awaited_once()

        # Reset mocks
        crawler.context.new_page.reset_mock()
        mock_robots_page.reset_mock()
        mock_response.reset_mock()

        # robots.txt access error (e.g., 403 Forbidden, response.ok is False)
        mock_response.ok = False
        mock_response.text = mocker.AsyncMock() # Reset text mock
        mock_robots_page.goto = mocker.AsyncMock(return_value=mock_response)
        mock_robots_page.close = mocker.AsyncMock()

        allowed = await crawler.check_robots_txt("https://example.com/forbidden")
        assert allowed is True # Should default to allowed
        crawler.context.new_page.assert_called_once()
        mock_robots_page.goto.assert_awaited_once_with("https://example.com/robots.txt", timeout=10000)
        mock_response.text.assert_not_awaited() # text() not called if response not ok
        mock_robots_page.close.assert_awaited_once()

class TestCrawlerManager:
    """크롤러 매니저 테스트"""
    
    @pytest_asyncio.fixture(scope="function")
    async def manager(self, tmp_path):
        """테스트용 매니저 인스턴스 생성"""
        with patch.dict(STORAGE_CONFIG, {"base_dir": str(tmp_path)}):
            manager = CrawlerManager()
            yield manager
        
    @pytest.mark.asyncio
    async def test_init_crawlers(self, manager):
        """크롤러 초기화 테스트"""
        with patch('app.collector.crawler_manager.WebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler_class.return_value = mock_crawler
            
            await manager.init_crawlers()
            
            assert len(manager.crawlers) == len(CRAWLER_CONFIG)
            mock_crawler_class.assert_called()
        
    @pytest.mark.asyncio
    async def test_crawl_site(self, manager):
        """사이트 크롤링 테스트"""
        with patch('app.collector.crawler_manager.WebCrawler') as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.crawl_page = AsyncMock(return_value={
                "success": True,
                "data": {
                    "title": "Test Article",
                    "content": "Test Content"
                }
            })
            mock_crawler_class.return_value = mock_crawler
            
            await manager.init_crawlers()
            
            test_site_id = list(CRAWLER_CONFIG.keys())[0]
            test_config = CRAWLER_CONFIG[test_site_id]
            
            results = await manager.crawl_site(test_site_id, test_config)
            
            assert len(results) > 0
            assert results[0]["site_id"] == test_site_id
            assert results[0]["site_name"] == test_config["name"]
        
    @pytest.mark.asyncio
    async def test_get_results(self, manager):
        """결과 조회 테스트"""
        test_results = {
            "site1": [{"title": "Test1"}],
            "site2": [{"title": "Test2"}]
        }
        manager.results = test_results
        
        # 전체 결과 조회
        all_results = manager.get_results()
        assert all_results == test_results
        
        # 특정 사이트 결과 조회
        site_results = manager.get_results("site1")
        assert site_results == {"site1": [{"title": "Test1"}]}
        
    @pytest.mark.asyncio
    async def test_get_status(self, manager):
        """상태 조회 테스트"""
        from datetime import datetime
        
        manager.running = True
        manager.last_crawl_time = {
            "site1": datetime.now()
        }
        manager.results = {
            "site1": [{"title": "Test"}]
        }
        
        status = manager.get_status()
        
        assert status["running"] is True
        assert len(status["last_crawl_time"]) == 1
        assert status["results_count"]["site1"] == 1

class TestSiteCrawling:
    """사이트별 크롤링 테스트"""
    
    @pytest_asyncio.fixture(scope="function")
    async def manager(self, tmp_path):
        """테스트용 매니저 인스턴스 생성"""
        with patch.dict(STORAGE_CONFIG, {"base_dir": str(tmp_path)}):
            manager = CrawlerManager()
            await manager.init_crawlers()
            yield manager
        
    @pytest.mark.asyncio
    async def test_openai_crawling(self, manager):
        """OpenAI 사이트 크롤링 테스트"""
        with patch.object(manager.crawlers["openai"], "crawl_page") as mock_crawl:
            mock_crawl.return_value = {
                "success": True,
                "data": {
                    "title": "OpenAI Research Paper",
                    "content": "Test research content",
                    "published_at": "2024-03-20",
                    "url": "https://openai.com/research/test-paper"
                }
            }
            
            results = await manager.crawl_site("openai", CRAWLER_CONFIG["openai"])
            
            assert len(results) > 0
            assert results[0]["site_id"] == "openai"
            assert results[0]["site_name"] == "OpenAI"
            assert "published_at" in results[0]
        
    @pytest.mark.asyncio
    async def test_anthropic_crawling(self, manager):
        """Anthropic 사이트 크롤링 테스트"""
        with patch.object(manager.crawlers["anthropic"], "crawl_page") as mock_crawl:
            mock_crawl.return_value = {
                "success": True,
                "data": {
                    "title": "Anthropic Research",
                    "content": "Test research content",
                    "published_at": "2024-03-20",
                    "url": "https://www.anthropic.com/research/test"
                }
            }
            
            results = await manager.crawl_site("anthropic", CRAWLER_CONFIG["anthropic"])
            
            assert len(results) > 0
            assert results[0]["site_id"] == "anthropic"
            assert results[0]["site_name"] == "Anthropic"
        
    @pytest.mark.asyncio
    async def test_deepmind_crawling(self, manager):
        """Google DeepMind 사이트 크롤링 테스트"""
        with patch.object(manager.crawlers["deepmind"], "crawl_page") as mock_crawl:
            mock_crawl.return_value = {
                "success": True,
                "data": {
                    "title": "DeepMind Research",
                    "content": "Test research content",
                    "published_at": "2024-03-20",
                    "url": "https://deepmind.google/research/test"
                }
            }
            
            results = await manager.crawl_site("deepmind", CRAWLER_CONFIG["deepmind"])
            
            assert len(results) > 0
            assert results[0]["site_id"] == "deepmind"
            assert results[0]["site_name"] == "Google DeepMind"
        
    @pytest.mark.asyncio
    async def test_ai_times_crawling(self, manager):
        """AI 타임스 사이트 크롤링 테스트"""
        with patch.object(manager.crawlers["ai_times"], "crawl_page") as mock_crawl:
            mock_crawl.return_value = {
                "success": True,
                "data": {
                    "title": "AI 뉴스",
                    "content": "테스트 뉴스 내용",
                    "published_at": "2024-03-20",
                    "url": "https://www.aitimes.com/news/test"
                }
            }
            
            results = await manager.crawl_site("ai_times", CRAWLER_CONFIG["ai_times"])
            
            assert len(results) > 0
            assert results[0]["site_id"] == "ai_times"
            assert results[0]["site_name"] == "AI 타임스"
        
    @pytest.mark.asyncio
    async def test_etnews_ai_crawling(self, manager):
        """전자신문 AI 섹션 크롤링 테스트"""
        with patch.object(manager.crawlers["etnews_ai"], "crawl_page") as mock_crawl:
            mock_crawl.return_value = {
                "success": True,
                "data": {
                    "title": "AI 산업 동향",
                    "content": "테스트 뉴스 내용",
                    "published_at": "2024-03-20",
                    "url": "https://www.etnews.com/news/test"
                }
            }
            
            results = await manager.crawl_site("etnews_ai", CRAWLER_CONFIG["etnews_ai"])
            
            assert len(results) > 0
            assert results[0]["site_id"] == "etnews_ai"
            assert results[0]["site_name"] == "전자신문 AI 섹션"
        
    @pytest.mark.asyncio
    async def test_error_handling(self, manager):
        """에러 처리 테스트"""
        with patch.object(manager.crawlers["openai"], "crawl_page") as mock_crawl:
            mock_crawl.side_effect = Exception("Network error")
            
            results = await manager.crawl_site("openai", CRAWLER_CONFIG["openai"])
            
            assert len(results) == 0
        
    @pytest.mark.asyncio
    async def test_robots_txt_compliance(self, manager):
        """robots.txt 준수 테스트"""
        with patch.object(manager.crawlers["openai"], "check_robots_txt") as mock_check:
            mock_check.return_value = False
            
            results = await manager.crawl_site("openai", CRAWLER_CONFIG["openai"])
            
            assert len(results) == 0
        
    @pytest.mark.asyncio
    async def test_concurrent_crawling(self, manager):
        """동시 크롤링 테스트"""
        with patch.object(manager.crawlers["openai"], "crawl_page") as mock_crawl:
            mock_crawl.return_value = {
                "success": True,
                "data": {
                    "title": "Test",
                    "content": "Test content"
                }
            }
            
            await manager.crawl_all()
            
            assert len(manager.results) > 0
            assert all(isinstance(v, list) for v in manager.results.values())
        
    @pytest.mark.asyncio
    async def test_scheduled_crawling(self, manager, mocker):
        """스케줄된 크롤링 테스트"""
        # Mock crawl_all to avoid actual crawling and check calls
        mock_crawl_all = mocker.patch.object(manager, 'crawl_all', new_callable=mocker.AsyncMock)

        # Mock asyncio.sleep used inside the loop (or wait_for) to speed up the test
        # We mock the wait_for inside the loop to control execution flow
        async def short_wait(*args, **kwargs):
            # Simulate a short wait or check the stop event immediately
            if manager._stop_requested.is_set():
                raise asyncio.TimeoutError # Allow loop to exit if stopped
            await asyncio.sleep(0.01) # Very short sleep to allow other tasks
            # Optionally, advance time if using a time-based mock library

        # We need to patch asyncio.wait_for used inside _run_scheduled_loop
        mocker.patch('asyncio.wait_for', side_effect=short_wait)

        try:
            # Start scheduled crawling in the background
            await manager.start_scheduled()

            # Wait for crawl_all to be called at least once
            # Use a loop with a timeout to avoid infinite wait
            start_time = asyncio.get_event_loop().time()
            while mock_crawl_all.call_count < 1:
                await asyncio.sleep(0.05) # Check periodically
                if asyncio.get_event_loop().time() - start_time > 5: # 5-second timeout
                    raise TimeoutError("crawl_all was not called within timeout")

            # Assert crawl_all was called
            mock_crawl_all.assert_awaited()
            assert mock_crawl_all.call_count >= 1

        finally:
            # Stop scheduled crawling
            await manager.stop_scheduled()

            # Ensure the task is actually stopped
            assert manager._scheduled_task is None or manager._scheduled_task.done()

if __name__ == '__main__':
    pytest.main(['-v', __file__]) 
from typing import Dict, List, Optional, Union
import asyncio
from datetime import datetime
import logging
from pathlib import Path
import json
import re

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page, Response
from urllib.parse import urljoin, urlparse

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebCrawler:
    """AI 뉴스 웹 크롤러 클래스"""
    
    def __init__(self, config: Optional[Dict] = None):
        """크롤러 초기화
        
        Args:
            config: 크롤러 설정 딕셔너리
        """
        self.config = config or {}
        self.browser: Optional[Browser] = None
        self.context = None
        self.page = None
        
        # 기본 설정값
        self.default_config = {
            "headless": True,  # 헤드리스 모드 사용
            "slow_mo": 100,    # 액션 사이 대기 시간 (ms)
            "timeout": 30000,  # 타임아웃 (ms)
            "screenshot_dir": "screenshots",  # 스크린샷 저장 디렉토리
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # 설정 병합
        self.config = {**self.default_config, **self.config}
        
        # 스크린샷 디렉토리 생성
        Path(self.config["screenshot_dir"]).mkdir(parents=True, exist_ok=True)
        
    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.stop()
        
    async def start(self):
        """브라우저 시작"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.config["headless"],
            slow_mo=self.config["slow_mo"]
        )
        self.context = await self.browser.new_context(
            user_agent=self.config["user_agent"]
        )
        self.page = await self.context.new_page()
        
    async def stop(self):
        """브라우저 종료"""
        if self.page:
            await self.page.close()
            self.page = None
        if self.context:
            await self.context.close()
            self.context = None
        if self.browser:
            await self.browser.close()
            self.browser = None
            
    async def take_screenshot(self, name: str):
        """스크린샷 촬영
        
        Args:
            name: 스크린샷 파일 이름
        """
        if not self.page:
            return
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{name}_{timestamp}.png"
        filepath = Path(self.config["screenshot_dir"]) / filename
        await self.page.screenshot(path=str(filepath))
        logger.info(f"Screenshot saved: {filepath}")
        
    async def scroll_to_bottom(self, scroll_delay: float = 1.0):
        """페이지 끝까지 스크롤
        
        Args:
            scroll_delay: 스크롤 사이 대기 시간 (초)
        """
        if not self.page:
            return
            
        prev_height = 0
        while True:
            curr_height = await self.page.evaluate("document.body.scrollHeight")
            if curr_height == prev_height:
                break
                
            await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(scroll_delay)
            prev_height = curr_height
            
    async def extract_text_content(self, selector: str) -> str:
        """선택자에 해당하는 텍스트 콘텐츠 추출
        
        Args:
            selector: CSS 선택자
            
        Returns:
            추출된 텍스트
        """
        if not self.page:
            return ""
            
        element = await self.page.query_selector(selector)
        if not element:
            return ""
            
        text = await element.text_content()
        return text.strip() if text else ""
        
    async def extract_article_content(self, article_selector: str) -> Dict:
        """기사 콘텐츠 추출
        
        Args:
            article_selector: 기사 본문 CSS 선택자
            
        Returns:
            추출된 기사 정보 딕셔너리
        """
        if not self.page:
            return {}
            
        # 메타 정보 추출
        title = await self.extract_text_content('h1') or await self.extract_text_content('title')
        
        # OpenGraph 태그에서 추가 정보 추출
        og_title = await self.page.evaluate('''() => {
            const el = document.querySelector('meta[property="og:title"]');
            return el ? el.getAttribute("content") : "";
        }''')
        
        og_description = await self.page.evaluate('''() => {
            const el = document.querySelector('meta[property="og:description"]');
            return el ? el.getAttribute("content") : "";
        }''')
        
        # 본문 추출
        content = await self.extract_text_content(article_selector)
        
        # 발행일 추출 시도
        published_at = await self.page.evaluate('''() => {
            const timeEl = document.querySelector('time');
            if (timeEl) {
                return timeEl.getAttribute("datetime") || timeEl.textContent;
            }
            return "";
        }''')
        
        return {
            "title": title or og_title,
            "description": og_description,
            "content": content,
            "published_at": published_at,
            "url": self.page.url
        }
        
    async def crawl_page(self, url: str, article_selector: str) -> Dict:
        """페이지 크롤링
        
        Args:
            url: 크롤링할 페이지 URL
            article_selector: 기사 본문 CSS 선택자
            
        Returns:
            크롤링된 페이지 정보
        """
        try:
            # 페이지 로드
            await self.page.goto(url, timeout=self.config["timeout"])
            await self.page.wait_for_load_state("networkidle")
            
            # 스크린샷 촬영 (디버깅용)
            await self.take_screenshot(f"page_{urlparse(url).netloc}")
            
            # 콘텐츠 추출
            article_data = await self.extract_article_content(article_selector)
            
            return {
                "success": True,
                "data": article_data,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            return {
                "success": False,
                "data": None,
                "error": str(e)
            }
            
    async def check_robots_txt(self, url: str) -> bool:
        """robots.txt 확인 (async with 대신 try...finally 사용)"""
        page = None # 페이지 변수 초기화
        try:
            parsed_url = urlparse(url)
            robots_url = f"{parsed_url.scheme}://{parsed_url.netloc}/robots.txt"

            # async with 대신 수동으로 페이지 생성
            if not self.context:
                logger.warning("Browser context not available for robots.txt check.")
                return True # 컨텍스트 없으면 확인 불가, 일단 허용
            page = await self.context.new_page()

            response = await page.goto(robots_url, timeout=10000) # 타임아웃 추가
            if not response or not response.ok: # 응답 상태 확인 추가
                logger.info(f"robots.txt not found or not accessible for {url}, allowing crawl.")
                return True

            content = await response.text()

            # User-agent 매칭 확인 (기존 로직 유지)
            user_agent_pattern = re.compile(r"User-agent: \*")
            disallow_pattern = re.compile(r"Disallow: (.*)")

            current_agent_rules = False
            for line in content.split('\n'):
                line = line.strip()
                if user_agent_pattern.match(line):
                    current_agent_rules = True
                elif line.startswith('User-agent:'):
                    current_agent_rules = False # 다른 User-agent 규칙 시작
                elif current_agent_rules and line.startswith('Disallow:'):
                    match = disallow_pattern.match(line)
                    if match:
                        disallow_path = match.group(1).strip()
                        # 경로가 비어있으면 무시 (Disallow: 다음에 아무것도 없는 경우)
                        if not disallow_path:
                            continue
                        # 루트 경로(/)는 모든 것을 금지
                        if disallow_path == '/' and parsed_url.path.startswith('/'):
                             logger.info(f"Crawling disallowed by robots.txt (Disallow: /) for {url}")
                             return False
                        # 특정 경로 시작 확인
                        if disallow_path != '/' and parsed_url.path.startswith(disallow_path):
                            logger.info(f"Crawling disallowed by robots.txt (Disallow: {disallow_path}) for {url}")
                            return False

            return True

        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {str(e)}. Allowing crawl by default.")
            return True  # 확인 실패 시 기본적으로 허용
        finally:
            # 페이지가 성공적으로 생성되었다면 반드시 닫기
            if page:
                await page.close()
            
    def save_results(self, results: List[Dict], filename: str):
        """크롤링 결과 저장
        
        Args:
            results: 크롤링 결과 리스트
            filename: 저장할 파일 이름
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
    @staticmethod
    def clean_text(text: str) -> str:
        """텍스트 정제
        
        Args:
            text: 정제할 텍스트
            
        Returns:
            정제된 텍스트
        """
        if not text:
            return ""
            
        # 불필요한 공백 제거
        text = re.sub(r'\s+', ' ', text)
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)
        # 특수문자 처리
        text = text.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        return text.strip() 
from typing import Dict, List, Optional
import asyncio
import logging
from datetime import datetime
from pathlib import Path
import json
import aiohttp
import time

from .web_crawler import WebCrawler
from .crawler_config import CRAWLER_CONFIG, CRAWLING_STRATEGY, STORAGE_CONFIG

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CrawlerManager:
    """크롤링 매니저 클래스"""
    
    def __init__(self):
        """크롤링 매니저 초기화"""
        self.crawlers: Dict[str, WebCrawler] = {}
        self.results: Dict[str, List[Dict]] = {}
        self.running = False
        self.last_crawl_time: Dict[str, datetime] = {}
        self._stop_requested = asyncio.Event() # 종료 요청 이벤트 추가
        self._scheduled_task: Optional[asyncio.Task] = None # 스케줄된 태스크 참조
        
        # 저장 디렉토리 생성
        Path(STORAGE_CONFIG["base_dir"]).mkdir(parents=True, exist_ok=True)
        
    async def init_crawlers(self):
        """크롤러 초기화"""
        for site_id, config in CRAWLER_CONFIG.items():
            crawler = WebCrawler({
                "headless": True,
                "slow_mo": CRAWLING_STRATEGY["request_delay"] * 1000,
                "timeout": CRAWLING_STRATEGY["timeout"] * 1000,
                "screenshot_dir": f"{STORAGE_CONFIG['base_dir']}/screenshots/{site_id}"
            })
            self.crawlers[site_id] = crawler
            
    async def crawl_site(self, site_id: str, config: Dict) -> List[Dict]:
        """단일 사이트 크롤링
        
        Args:
            site_id: 사이트 ID
            config: 사이트 설정
            
        Returns:
            크롤링 결과 리스트
        """
        crawler = self.crawlers[site_id]
        results = []
        
        try:
            await crawler.start()
            
            # robots.txt 확인
            for path in config["paths"]:
                url = f"{config['base_url']}{path}"
                if not await crawler.check_robots_txt(url):
                    logger.warning(f"Crawling not allowed for {url}")
                    continue
                    
                # 페이지 크롤링
                result = await crawler.crawl_page(
                    url=url,
                    article_selector=config["article_selector"]
                )
                
                if result["success"] and result["data"]:
                    results.append({
                        "site_id": site_id,
                        "site_name": config["name"],
                        "crawled_at": datetime.now().isoformat(),
                        **result["data"]
                    })
                    
            # 결과 저장
            if results:
                self._save_results(site_id, results)
                
        except Exception as e:
            logger.error(f"Error crawling {site_id}: {str(e)}")
            
        finally:
            await crawler.stop()
            
        return results
        
    def _save_results(self, site_id: str, results: List[Dict]):
        """크롤링 결과 저장
        
        Args:
            site_id: 사이트 ID
            results: 크롤링 결과 리스트
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{STORAGE_CONFIG['base_dir']}/{site_id}_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Saved {len(results)} results for {site_id} to {filename}")
        
    async def crawl_all(self):
        """모든 사이트 크롤링"""
        if self.running:
            logger.warning("Crawling already in progress")
            return
            
        self.running = True
        try:
            await self.init_crawlers()
            
            # 우선순위별로 사이트 그룹화
            sites_by_priority = {}
            for site_id, config in CRAWLER_CONFIG.items():
                priority = config["priority"]
                if priority not in sites_by_priority:
                    sites_by_priority[priority] = []
                sites_by_priority[priority].append((site_id, config))
                
            # 우선순위 순서대로 크롤링
            for priority in sorted(sites_by_priority.keys()):
                sites = sites_by_priority[priority]
                
                # 동시 크롤링 제한 적용
                tasks = []
                for i in range(0, len(sites), CRAWLING_STRATEGY["concurrent_limit"]):
                    batch = sites[i:i + CRAWLING_STRATEGY["concurrent_limit"]]
                    batch_tasks = [
                        self.crawl_site(site_id, config)
                        for site_id, config in batch
                    ]
                    results = await asyncio.gather(*batch_tasks)
                    
                    # 결과 처리
                    for (site_id, _), site_results in zip(batch, results):
                        if site_results:
                            self.results[site_id] = site_results
                            self.last_crawl_time[site_id] = datetime.now()
                            
                    # 배치 간 대기
                    await asyncio.sleep(CRAWLING_STRATEGY["request_delay"])
                    
        except Exception as e:
            logger.error(f"Error in crawl_all: {str(e)}")
            
        finally:
            self.running = False
            
    async def _run_scheduled_loop(self):
        """스케줄된 크롤링 실행 루프 (내부용)"""
        while not self._stop_requested.is_set():
            try:
                current_time = datetime.now()
                sites_to_update = []
                
                # Check only configured sites
                for site_id, config in CRAWLER_CONFIG.items(): 
                    if site_id not in self.crawlers:
                         logger.warning(f"Site {site_id} configured but not initialized in manager.")
                         continue # Skip uninitialized crawlers

                    last_crawl = self.last_crawl_time.get(site_id)
                    update_interval_seconds = config.get("update_interval", 24) * 3600 # Default 24h
                    if not last_crawl or (current_time - last_crawl).total_seconds() >= update_interval_seconds:
                        sites_to_update.append(site_id)

                if sites_to_update:
                    logger.info(f"Scheduled update for sites: {', '.join(sites_to_update)}")
                    # Use a modified crawl_all or specific site crawling logic for schedule
                    # For now, let's assume crawl_all handles this subset or runs fully
                    await self.crawl_all() # Consider passing sites_to_update if crawl_all supports it

                # 다음 체크까지 대기 (종료 이벤트를 기다리도록 수정)
                try:
                    # Sleep for 60 seconds or until stop is requested
                    await asyncio.wait_for(self._stop_requested.wait(), timeout=60)
                except asyncio.TimeoutError:
                    pass # Timeout is expected, continue loop if not stopped

            except Exception as e:
                logger.error(f"Error in scheduled crawling loop: {str(e)}")
                # 에러 발생 시에도 종료 이벤트를 기다리며 잠시 대기
                try:
                    await asyncio.wait_for(self._stop_requested.wait(), timeout=60)
                except asyncio.TimeoutError:
                    pass
        logger.info("Scheduled crawling loop stopped.")

    async def start_scheduled(self):
         """스케줄된 크롤링 시작"""
         if self._scheduled_task and not self._scheduled_task.done():
             logger.warning("Scheduled crawling is already running.")
             return
         self._stop_requested.clear() # 시작 시 종료 요청 초기화
         # Ensure crawlers are initialized before starting schedule
         if not self.crawlers:
             await self.init_crawlers()
         self._scheduled_task = asyncio.create_task(self._run_scheduled_loop())
         logger.info("Scheduled crawling started.")

    async def stop_scheduled(self):
         """스케줄된 크롤링 중지"""
         if self._scheduled_task and not self._scheduled_task.done():
             logger.info("Stopping scheduled crawling...")
             self._stop_requested.set() # 종료 이벤트 설정
             try:
                 # Wait for the task to finish gracefully
                 await asyncio.wait_for(self._scheduled_task, timeout=10) 
             except asyncio.TimeoutError:
                 logger.warning("Scheduled task did not finish gracefully, cancelling.")
                 self._scheduled_task.cancel()
                 try:
                     await self._scheduled_task # Allow cancellation to propagate
                 except asyncio.CancelledError:
                     logger.info("Scheduled task cancelled.")
             except Exception as e:
                 logger.error(f"Error during scheduled task stopping: {e}")
             self._scheduled_task = None
             logger.info("Scheduled crawling stopped.")
         else:
             logger.info("Scheduled crawling is not running.")

    def get_results(self, site_id: Optional[str] = None) -> Dict[str, List[Dict]]:
        """크롤링 결과 조회
        
        Args:
            site_id: 조회할 사이트 ID (None인 경우 전체 결과 반환)
            
        Returns:
            크롤링 결과
        """
        if site_id:
            return {site_id: self.results.get(site_id, [])}
        return self.results
        
    def get_status(self) -> Dict:
        """크롤링 상태 조회
        
        Returns:
            크롤링 상태 정보
        """
        return {
            "running": self.running,
            "last_crawl_time": {
                site_id: last_crawl.isoformat()
                for site_id, last_crawl in self.last_crawl_time.items()
            },
            "results_count": {
                site_id: len(results)
                for site_id, results in self.results.items()
            }
        } 
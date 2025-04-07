import asyncio
import logging
from pathlib import Path
import sys
import signal
from typing import Optional

from .crawler_manager import CrawlerManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('crawler.log')
    ]
)
logger = logging.getLogger(__name__)

async def run_crawler(mode: str = "scheduled"):
    """크롤러 실행
    
    Args:
        mode: 실행 모드 ("scheduled" 또는 "once")
    """
    manager = CrawlerManager()
    
    def signal_handler(signum, frame):
        logger.info("Stopping crawler...")
        manager.running = False
        sys.exit(0)
        
    # 시그널 핸들러 등록
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if mode == "scheduled":
            logger.info("Starting scheduled crawler...")
            await manager.run_scheduled()
        else:
            logger.info("Running one-time crawl...")
            await manager.crawl_all()
            
    except Exception as e:
        logger.error(f"Error running crawler: {str(e)}")
        raise
        
def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run web crawler")
    parser.add_argument(
        "--mode",
        choices=["scheduled", "once"],
        default="scheduled",
        help="Crawler run mode"
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_crawler(args.mode))
    except KeyboardInterrupt:
        logger.info("Crawler stopped by user")
    except Exception as e:
        logger.error(f"Crawler failed: {str(e)}")
        sys.exit(1)
        
if __name__ == "__main__":
    main() 
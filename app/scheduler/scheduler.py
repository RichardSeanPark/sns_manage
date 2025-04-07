import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

# 로깅 설정
logger = logging.getLogger(__name__)

# TODO: 데이터베이스 URL 설정 로드 (예: config.py 또는 환경 변수)
DATABASE_URL = "sqlite:///jobs.sqlite"

jobstores = {
    'default': SQLAlchemyJobStore(url=DATABASE_URL)
}
executors = {
    'default': ThreadPoolExecutor(20),
    'processpool': ProcessPoolExecutor(5)
}
job_defaults = {
    'coalesce': False,
    'max_instances': 3
}

scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone='Asia/Seoul'  # 시스템에 맞는 타임존 설정
)

def start_scheduler():
    """스케줄러를 시작합니다."""
    if not scheduler.running:
        try:
            scheduler.start()
            logger.info("스케줄러가 성공적으로 시작되었습니다.")
        except Exception as e:
            logger.error(f"스케줄러 시작 중 오류 발생: {e}")
    else:
        logger.info("스케줄러가 이미 실행 중입니다.")

def stop_scheduler():
    """스케줄러를 종료합니다."""
    if scheduler.running:
        try:
            scheduler.shutdown()
            logger.info("스케줄러가 성공적으로 종료되었습니다.")
        except Exception as e:
            logger.error(f"스케줄러 종료 중 오류 발생: {e}")

def add_crawl_job(site_config):
    """크롤링 작업을 스케줄러에 추가합니다.

    Args:
        site_config (dict): 사이트 설정 정보 (URL, 크롤링 주기, 우선순위 등 포함)
    """
    # TODO: site_config에서 필요한 정보 추출 (job_id, trigger, func 등)
    job_id = f"crawl_{site_config['name']}" # 예시 ID
    crawl_interval_minutes = site_config.get('interval_minutes', 60) # 기본 60분

    # TODO: 실제 크롤링 함수 연결 (예: collector 모듈의 함수)
    def dummy_crawl_func(url):
        logger.info(f"Crawling {url}...")
        # 실제 크롤링 로직 호출
        pass

    try:
        scheduler.add_job(
            dummy_crawl_func,
            'interval',
            minutes=crawl_interval_minutes,
            id=job_id,
            args=[site_config['url']],
            replace_existing=True,
            misfire_grace_time=600 # 10분
            # TODO: 우선순위 관련 설정 추가 (executor 등)
        )
        logger.info(f"크롤링 작업 추가됨: {job_id}, 주기: {crawl_interval_minutes}분")
    except Exception as e:
        logger.error(f"작업 추가 중 오류 발생 ({job_id}): {e}")

def load_scheduled_jobs():
    """설정 파일이나 DB에서 작업 설정을 로드하여 스케줄러에 추가합니다."""
    # TODO: 설정 파일(config.py) 또는 데이터베이스에서 사이트별 크롤링 설정 로드
    # 예시 설정 (실제로는 외부에서 로드)
    example_sites = [
        {'name': 'example_site_1', 'url': 'http://example.com/news', 'interval_minutes': 30, 'priority': 1},
        {'name': 'example_site_2', 'url': 'http://example.org/ai', 'interval_minutes': 120, 'priority': 2},
    ]
    for site in example_sites:
        add_crawl_job(site)

# 애플리케이션 시작 시 스케줄러 시작 및 작업 로드
# 예: FastAPI의 startup 이벤트 핸들러 등에서 호출
# start_scheduler()
# load_scheduled_jobs() 
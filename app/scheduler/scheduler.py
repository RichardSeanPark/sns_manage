import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.base import JobLookupError

# tasks.py에서 실제 작업 함수를 가져옵니다.
from .tasks import collect_data_task

# 설정 파일 가져오기
from .config import SCHEDULE_CONFIG, SOURCE_CONFIG, SCHEDULER_SETTINGS

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 스케줄러 인스턴스 생성 (설정 직접 전달)
try:
    scheduler = BackgroundScheduler(**SCHEDULER_SETTINGS)
    logger.info("Scheduler initialized with settings from config.")
except Exception as e:
    logger.error(f"Failed to initialize scheduler with settings: {e}", exc_info=True)
    logger.warning("Initializing scheduler with default settings.")
    scheduler = BackgroundScheduler()

def add_collection_jobs():
    """설정 파일을 기반으로 데이터 수집 작업을 스케줄러에 추가합니다."""
    logger.info("Adding data collection jobs to the scheduler...")
    added_count = 0
    skipped_count = 0
    for url, config in SOURCE_CONFIG.items():
        schedule_type = config.get('schedule_type')
        priority = config.get('priority', 5) # 기본 우선순위 설정
        schedule_info = SCHEDULE_CONFIG.get(schedule_type)

        if not schedule_info:
            logger.warning(f"Schedule type '{schedule_type}' not found for source: {url}. Skipping.")
            skipped_count += 1
            continue

        trigger = schedule_info.get('trigger')
        if not trigger:
            logger.warning(f"Trigger not defined for schedule type '{schedule_type}'. Skipping source: {url}.")
            skipped_count += 1
            continue

        job_id = f"collect_{url}" # URL 기반 고유 작업 ID

        try:
            # 실제 작업 함수(collect_data_task) 사용
            scheduler.add_job(
                collect_data_task, # 실제 작업 함수 사용
                trigger=trigger,
                args=[url, priority],
                id=job_id,
                name=f"Collect data from {url}",
                replace_existing=True # 동일 ID 작업 존재 시 교체
            )
            logger.debug(f"Added job: {job_id} for {url} with schedule '{schedule_type}' and priority {priority}")
            added_count += 1
        except Exception as e:
            logger.error(f"Failed to add job for {url}: {e}")
            skipped_count += 1

    logger.info(f"Finished adding jobs. Added: {added_count}, Skipped/Failed: {skipped_count}")

def start_scheduler():
    """스케줄러를 시작합니다."""
    if not scheduler.running:
        try:
            add_collection_jobs() # 시작 전 작업 추가
            scheduler.start()
            logger.info("Scheduler started successfully.")
        except Exception as e:
            logger.error(f"Failed to start the scheduler: {e}")
    else:
        logger.info("Scheduler is already running.")

def stop_scheduler():
    """스케줄러를 안전하게 중지합니다."""
    if scheduler.running:
        try:
            scheduler.shutdown()
            logger.info("Scheduler stopped successfully.")
        except Exception as e:
            logger.error(f"Failed to stop the scheduler: {e}")
    else:
        logger.info("Scheduler is not running.")

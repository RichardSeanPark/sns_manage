import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from app.config import DATABASE_URL, DB_CONNECT_ARGS # DB URL 가져오기

logger = logging.getLogger(__name__)

# 스케줄러 설정
# 여기서는 작업 저장소로 SQLite 사용 (메모리 대신 영구 저장)
# DATABASE_URL을 jobstore URL로 사용
jobstores = {
    # default jobstore는 DB 사용
    'default': SQLAlchemyJobStore(url=DATABASE_URL)
}
executors = {
    'default': AsyncIOExecutor()
}
job_defaults = {
    'coalesce': False, # 동일 작업 동시 실행 방지
    'max_instances': 1   # 동일 작업 최대 1개 인스턴스만 실행
}

# 스케줄러 인스턴스 생성 (전역으로 접근 가능하도록)
scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone='UTC' # 또는 Asia/Seoul 등 로컬 타임존
)

def start_scheduler():
    """스케줄러를 시작합니다."""
    if not scheduler.running:
        try:
            # TODO: 필요한 기본 작업들을 여기서 추가할 수 있음
            # from .tasks import collect_rss_feeds_task
            # scheduler.add_job(collect_rss_feeds_task, 'interval', hours=1, id='rss_collection_hourly')

            scheduler.start()
            logger.info("Scheduler started.")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}", exc_info=True)
    else:
        logger.info("Scheduler is already running.")

def shutdown_scheduler():
    """스케줄러를 종료합니다."""
    if scheduler.running:
        try:
            scheduler.shutdown()
            logger.info("Scheduler shut down.")
        except Exception as e:
            logger.error(f"Failed to shut down scheduler: {e}", exc_info=True)

# 스케줄러 관련 함수들 추가 (도구에서 사용할 수 있도록)
def add_job_to_scheduler(func, trigger, **kwargs):
    """스케줄러에 작업을 추가합니다."""
    try:
        job = scheduler.add_job(func, trigger, **kwargs)
        logger.info(f"Job '{kwargs.get('id', job.id)}' added with trigger: {trigger}")
        return job.id
    except Exception as e:
        logger.error(f"Failed to add job {kwargs.get('id', 'N/A')}: {e}", exc_info=True)
        return None

def get_job_status(job_id: str):
    """특정 작업의 상태를 조회합니다."""
    try:
        job = scheduler.get_job(job_id)
        if job:
            return {
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            }
        else:
            return None
    except Exception as e:
        logger.error(f"Failed to get job status for {job_id}: {e}", exc_info=True)
        return None

def list_all_jobs():
     """스케줄러에 등록된 모든 작업 목록을 반환합니다."""
     try:
         jobs = scheduler.get_jobs()
         return [
             {
                 "id": job.id,
                 "name": job.name,
                 "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
                 "trigger": str(job.trigger)
             } for job in jobs
         ]
     except Exception as e:
         logger.error(f"Failed to list jobs: {e}", exc_info=True)
         return []

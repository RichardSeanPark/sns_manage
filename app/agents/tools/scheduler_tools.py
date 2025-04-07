import logging
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, validator, root_validator, datetime_parse # datetime_parse 추가
from importlib import import_module
from datetime import datetime # datetime 직접 임포트
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
# DateTrigger 임포트 추가
from apscheduler.triggers.date import DateTrigger

# agents 임포트 시도 - 라이브러리가 설치되어 있지 않으면 오류 발생 가능
try:
    from agents import tool
except ImportError:
    # 대체 데코레이터 정의 (라이브러리 없을 경우 임시 사용)
    def tool(func):
        return func
    logger = logging.getLogger(__name__)
    logger.warning("Could not import 'agents' library. Using dummy 'tool' decorator.")


from app.scheduler.scheduler import add_job_to_scheduler, get_job_status, list_all_jobs # 스케줄러 유틸리티 함수 임포트

logger = logging.getLogger(__name__)

def find_runnable(path: str):
    """점(.)으로 구분된 경로 문자열을 받아 실제 실행 가능한 객체(함수 등)를 반환합니다."""
    try:
        module_path, object_name = path.rsplit('.', 1)
        module = import_module(module_path)
        runnable = getattr(module, object_name)
        if not callable(runnable):
            raise TypeError(f"Object at path '{path}' is not callable.")
        return runnable
    except (ImportError, AttributeError, ValueError, TypeError) as e:
        logger.error(f"Could not find or load runnable function at path '{path}': {e}")
        raise ImportError(f"Could not find runnable function at path '{path}': {e}") from e

# --- Schedule Collection Task Tool ---

class ScheduleTaskInput(BaseModel):
    function_path: str = Field(description="실행할 함수의 전체 경로 (예: 'app.scheduler.tasks.collect_rss_feeds_task')")
    trigger_type: Literal['interval', 'cron', 'date'] = Field(description="스케줄링 트리거 타입 ('interval', 'cron', 'date')")
    trigger_args: Dict[str, Any] = Field(description="트리거 생성에 필요한 인자 (APScheduler 문서 참조)")
    job_id: Optional[str] = Field(default=None, description="작업의 고유 ID (지정하지 않으면 자동 생성)")
    job_name: Optional[str] = Field(default=None, description="작업의 이름 (지정하지 않으면 함수 경로 사용)")
    replace_existing: bool = Field(default=False, description="동일 ID의 작업이 존재할 경우 덮어쓸지 여부")

    @validator('trigger_args')
    def check_trigger_args(cls, v, values):
        trigger_type = values.get('trigger_type')
        if not trigger_type:
            return v # trigger_type 검증이 먼저 실패한 경우

        # TODO: 각 trigger_type에 맞는 필수 인자가 있는지 더 상세히 검증할 수 있음
        # 예: interval -> 'seconds' or 'minutes' or 'hours' 등 필요
        # 예: cron -> 'hour', 'minute' 등 필요
        if not isinstance(v, dict):
            raise ValueError("trigger_args must be a dictionary")
        return v

@tool
async def schedule_collection_task_tool(input_data: ScheduleTaskInput) -> Optional[Dict[str, str]]:
    """
    지정된 함수를 스케줄러에 등록합니다.
    성공 시 {'job_id': 생성된_job_id}를 반환하고, 실패 시 None을 반환합니다.
    """
    logger.info(f"Tool 'schedule_collection_task_tool' called with input: {input_data}")
    try:
        # 1. 함수 경로 문자열을 실제 함수 객체로 변환
        runnable_func = find_runnable(input_data.function_path)

        # 2. 트리거 객체 생성
        trigger_class = None
        if input_data.trigger_type == 'interval':
            trigger_class = IntervalTrigger
        elif input_data.trigger_type == 'cron':
            trigger_class = CronTrigger
        elif input_data.trigger_type == 'date':
            trigger_class = DateTrigger # DateTrigger 사용
        else:
            # 이 경우는 Pydantic validator에서 걸러지지만 방어적으로 추가
            logger.error(f"Invalid trigger_type: {input_data.trigger_type}")
            return None

        trigger = trigger_class(**input_data.trigger_args)

        # 3. 스케줄러에 작업 추가 요청
        job_name = input_data.job_name or input_data.function_path # 이름 미지정 시 함수 경로 사용
        job_id = add_job_to_scheduler(
            func=runnable_func,
            trigger=trigger,
            id=input_data.job_id,
            name=job_name,
            replace_existing=input_data.replace_existing
            # 필요한 다른 APScheduler 옵션 추가 가능 (예: misfire_grace_time)
        )

        if job_id:
            logger.info(f"Successfully scheduled job '{job_name}' with ID: {job_id}")
            return {"job_id": job_id}
        else:
            logger.error(f"Failed to schedule job '{job_name}' (add_job_to_scheduler returned None).")
            return None

    except ImportError as e:
        # find_runnable에서 발생한 오류
        logger.error(f"Failed to schedule job due to ImportError: {e}")
        return None
    except Exception as e:
        logger.error(f"Error in schedule_collection_task_tool: {e}", exc_info=True)
        return None

# --- Check Task Status Tool ---

class CheckTaskInput(BaseModel):
    job_id: str = Field(description="상태를 조회할 작업의 ID")

class JobStatus(BaseModel):
    id: str
    name: str
    next_run_time: Optional[datetime]
    trigger: str

@tool
async def check_task_status_tool(input_data: CheckTaskInput) -> Optional[JobStatus]:
    """
    주어진 Job ID에 해당하는 스케줄된 작업의 상태를 조회합니다.
    작업이 존재하면 상태 정보를 담은 JobStatus 객체를 반환하고, 없으면 None을 반환합니다.
    """
    logger.info(f"Tool 'check_task_status_tool' called for job ID: {input_data.job_id}")
    try:
        status_dict = get_job_status(input_data.job_id)
        if status_dict:
            logger.info(f"Status for job '{input_data.job_id}': {status_dict}")
            # Pydantic 모델로 변환하여 반환
            return JobStatus(**status_dict)
        else:
            logger.info(f"Job with ID '{input_data.job_id}' not found.")
            return None
    except Exception as e:
        logger.error(f"Error checking job status for {input_data.job_id}: {e}", exc_info=True)
        return None

# --- List Scheduled Tasks Tool ---

@tool
async def list_scheduled_tasks_tool() -> List[JobStatus]:
    """
    현재 스케줄러에 등록된 모든 작업의 목록을 조회합니다.
    각 작업의 상태 정보를 담은 JobStatus 객체의 리스트를 반환합니다.
    """
    logger.info("Tool 'list_scheduled_tasks_tool' called.")
    try:
        jobs_list = list_all_jobs()
        logger.info(f"Found {len(jobs_list)} scheduled jobs.")
        # 각 딕셔너리를 Pydantic 모델로 변환
        return [JobStatus(**job_dict) for job_dict in jobs_list]
    except Exception as e:
        logger.error(f"Error listing scheduled jobs: {e}", exc_info=True)
        return []

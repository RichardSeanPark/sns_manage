import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

# 테스트 대상 도구 임포트
from app.agents.tools.scheduler_tools import (
    schedule_collection_task_tool,
    check_task_status_tool,
    list_scheduled_tasks_tool,
    ScheduleTaskInput,
    CheckTaskInput,
    JobStatus, # 반환 타입 확인용
)
# Pydantic 모델 사용
from pydantic import ValidationError

# --- Fixtures ---

# 각 도구가 사용하는 app.scheduler.scheduler 내의 함수들을 패치합니다.
# autouse=True로 설정하면 모든 테스트 함수에 자동으로 적용됩니다.

@pytest.fixture(autouse=True)
def patch_scheduler_functions():
    # 'app.agents.tools.scheduler_tools' 모듈 내에서 참조하는 함수들을 패치합니다.
    with patch('app.agents.tools.scheduler_tools.add_job_to_scheduler', return_value="mock_job_id_123") as mock_add, \
         patch('app.agents.tools.scheduler_tools.get_job_status') as mock_get, \
         patch('app.agents.tools.scheduler_tools.list_all_jobs') as mock_list, \
         patch('app.agents.tools.scheduler_tools.find_runnable') as mock_find: # find_runnable도 패치
        # find_runnable은 기본적으로 모의 함수 객체를 반환하도록 설정
        mock_find.return_value = AsyncMock() # 실제 함수가 아니므로 AsyncMock 등으로 대체
        yield mock_add, mock_get, mock_list, mock_find

@pytest.fixture
def sample_job_status_dict():
    """get_job_status가 반환할 샘플 딕셔너리"""
    return {
        "id": "sample_job_1",
        "name": "Sample Job",
        "next_run_time": datetime.now(timezone.utc).isoformat(),
        "trigger": "IntervalTrigger(seconds=60)"
    }

# --- Tests for schedule_collection_task_tool ---

@pytest.mark.asyncio
async def test_schedule_interval_job(patch_scheduler_functions):
    """Interval 트리거로 작업 추가 성공 및 job ID 반환 확인"""
    mock_add, _, _, mock_find = patch_scheduler_functions
    mock_find.return_value = print # 실제 실행 가능한 객체로 설정 (AsyncMock 가능)

    input_data = ScheduleTaskInput(
        function_path="app.scheduler.tasks.collect_rss_feeds_task", # 유효한 경로 가정
        trigger_type="interval",
        trigger_args={"seconds": 300},
    )
    result = await schedule_collection_task_tool(input_data)

    mock_find.assert_called_once_with("app.scheduler.tasks.collect_rss_feeds_task")
    mock_add.assert_called_once()
    # add_job_to_scheduler의 인자 확인
    call_args = mock_add.call_args.args # 위치 인자 튜플
    call_kwargs = mock_add.call_args.kwargs # 키워드 인자 사전

    # trigger가 키워드 인자로 전달되었는지 확인
    assert 'trigger' in call_kwargs, "'trigger' not found in keyword arguments"
    trigger_arg = call_kwargs['trigger']
    assert isinstance(trigger_arg, IntervalTrigger), f"Expected IntervalTrigger, got {type(trigger_arg)}"
    assert trigger_arg.interval.total_seconds() == 300
    # 나머지 키워드 인자 확인
    assert call_kwargs['func'] == mock_find.return_value
    assert call_kwargs['id'] is None # ID 미지정
    assert call_kwargs['name'] == "app.scheduler.tasks.collect_rss_feeds_task" # 기본값
    assert call_kwargs['replace_existing'] is False # 기본값
    assert result == {"job_id": "mock_job_id_123"}

@pytest.mark.asyncio
async def test_schedule_cron_job(patch_scheduler_functions):
    """Cron 트리거로 작업 추가 성공 확인"""
    mock_add, _, _, mock_find = patch_scheduler_functions
    mock_find.return_value = print

    input_data = ScheduleTaskInput(
        function_path="another.task",
        trigger_type="cron",
        trigger_args={"hour": "9", "minute": "30"},
        job_id="cron_job_test",
        job_name="My Cron Job",
        replace_existing=True,
    )
    result = await schedule_collection_task_tool(input_data)

    mock_find.assert_called_once_with("another.task")
    mock_add.assert_called_once()
    # 인자 확인
    call_args = mock_add.call_args.args
    call_kwargs = mock_add.call_args.kwargs

    # trigger가 키워드 인자로 전달되었는지 확인
    assert 'trigger' in call_kwargs, "'trigger' not found in keyword arguments"
    trigger_arg = call_kwargs['trigger']
    assert isinstance(trigger_arg, CronTrigger), f"Expected CronTrigger, got {type(trigger_arg)}"
    # 키워드 인자 확인
    assert call_kwargs['func'] == mock_find.return_value
    assert call_kwargs['id'] == "cron_job_test"
    assert call_kwargs['name'] == "My Cron Job"
    assert call_kwargs['replace_existing'] is True
    assert result == {"job_id": "mock_job_id_123"}

@pytest.mark.asyncio
async def test_schedule_invalid_function_path(patch_scheduler_functions, caplog):
    """잘못된 함수 경로 입력 시 None 반환 및 오류 로깅 확인"""
    mock_add, _, _, mock_find = patch_scheduler_functions
    error_msg = "Cannot find module or object"
    mock_find.side_effect = ImportError(error_msg) # 함수 찾기 실패 모의

    input_data = ScheduleTaskInput(
        function_path="invalid.path.nonexistent_func",
        trigger_type="interval",
        trigger_args={"seconds": 60},
    )
    result = await schedule_collection_task_tool(input_data)

    mock_find.assert_called_once_with("invalid.path.nonexistent_func")
    mock_add.assert_not_called() # add_job_to_scheduler 호출 안 됨
    assert result is None
    # 실제 로그 메시지 형식 확인 및 검증
    assert "Failed to schedule job due to ImportError" in caplog.text
    assert error_msg in caplog.text # 원래 예외 메시지 포함 확인

@pytest.mark.asyncio
async def test_schedule_invalid_trigger_type(patch_scheduler_functions, caplog):
    """잘못된 트리거 타입 입력 시 None 반환 및 오류 로깅 확인"""
    mock_add, _, _, mock_find = patch_scheduler_functions
    mock_find.return_value = print

    # Pydantic 모델에서 trigger_type 검증이 먼저 일어남
    with pytest.raises(ValidationError):
         ScheduleTaskInput(
            function_path="some.task",
            trigger_type="invalid_type", # 잘못된 타입
            trigger_args={"seconds": 60},
        )
    # 따라서 도달하기 전에 Pydantic에서 에러 발생, None 반환 로직 테스트 불필요
    # 만약 Pydantic 검증이 없다면 아래와 같이 테스트
    # input_data = ScheduleTaskInput(...)
    # result = await schedule_collection_task_tool(input_data)
    # assert result is None
    # assert "Invalid trigger_type" in caplog.text

@pytest.mark.asyncio
async def test_schedule_scheduler_add_error(patch_scheduler_functions, caplog):
    """스케줄러 작업 추가 실패 시 None 반환 및 오류 로깅 확인"""
    mock_add, _, _, mock_find = patch_scheduler_functions
    mock_find.return_value = print
    mock_add.return_value = None # add_job_to_scheduler 실패 모의

    input_data = ScheduleTaskInput(
        function_path="app.scheduler.tasks.collect_rss_feeds_task",
        trigger_type="interval",
        trigger_args={"seconds": 60},
    )
    result = await schedule_collection_task_tool(input_data)

    mock_find.assert_called_once()
    mock_add.assert_called_once() # 호출은 되었으나 실패
    assert result is None
    assert "Failed to schedule job" in caplog.text

# --- Tests for check_task_status_tool ---

@pytest.mark.asyncio
async def test_check_existing_job(patch_scheduler_functions, sample_job_status_dict):
    """존재하는 job ID 조회 시 JobStatus 객체 반환 확인"""
    _, mock_get, _, _ = patch_scheduler_functions
    mock_get.return_value = sample_job_status_dict

    input_data = CheckTaskInput(job_id="sample_job_1")
    result = await check_task_status_tool(input_data)

    # 위치 인자로 호출 확인
    mock_get.assert_called_once_with("sample_job_1")
    assert isinstance(result, JobStatus)
    assert result.id == "sample_job_1"
    assert result.name == "Sample Job"
    # datetime 객체로 변환되었는지 확인
    assert isinstance(result.next_run_time, datetime)
    assert result.trigger == "IntervalTrigger(seconds=60)"

@pytest.mark.asyncio
async def test_check_nonexistent_job(patch_scheduler_functions, caplog):
    """존재하지 않는 job ID 조회 시 None 반환 확인"""
    _, mock_get, _, _ = patch_scheduler_functions
    mock_get.return_value = None # Job 없음 모의

    input_data = CheckTaskInput(job_id="nonexistent_job")
    result = await check_task_status_tool(input_data)

    # 위치 인자로 호출 확인
    mock_get.assert_called_once_with("nonexistent_job")
    assert result is None
    # 별도 로그는 남기지 않음 (정상 동작)

@pytest.mark.asyncio
async def test_check_job_scheduler_error(patch_scheduler_functions, caplog):
    """스케줄러 조회 오류 발생 시 None 반환 및 로그 기록 확인"""
    _, mock_get, _, _ = patch_scheduler_functions
    mock_get.side_effect = Exception("Scheduler communication error")

    input_data = CheckTaskInput(job_id="some_job")
    result = await check_task_status_tool(input_data)

    # 위치 인자로 호출 확인
    mock_get.assert_called_once_with("some_job")
    assert result is None
    assert "Error checking job status for" in caplog.text
    assert "Scheduler communication error" in caplog.text

# --- Tests for list_scheduled_tasks_tool ---

@pytest.mark.asyncio
async def test_list_jobs_empty(patch_scheduler_functions):
    """스케줄된 작업 없을 때 빈 리스트 반환 확인"""
    _, _, mock_list, _ = patch_scheduler_functions
    mock_list.return_value = [] # 빈 목록 모의

    result = await list_scheduled_tasks_tool() # 입력 없음

    mock_list.assert_called_once_with()
    assert result == []

@pytest.mark.asyncio
async def test_list_jobs_multiple(patch_scheduler_functions, sample_job_status_dict):
    """여러 작업이 스케줄된 상태에서 올바른 목록 반환 확인"""
    _, _, mock_list, _ = patch_scheduler_functions
    job2_dict = sample_job_status_dict.copy()
    job2_dict["id"] = "another_job_2"
    job2_dict["name"] = "Another Job"
    mock_list.return_value = [sample_job_status_dict, job2_dict]

    result = await list_scheduled_tasks_tool()

    mock_list.assert_called_once_with()
    assert isinstance(result, list)
    assert len(result) == 2
    assert isinstance(result[0], JobStatus)
    assert result[0].id == "sample_job_1"
    assert isinstance(result[1], JobStatus)
    assert result[1].id == "another_job_2"

@pytest.mark.asyncio
async def test_list_jobs_scheduler_error(patch_scheduler_functions, caplog):
    """스케줄러 목록 조회 오류 시 빈 리스트 반환 및 로그 기록 확인"""
    _, _, mock_list, _ = patch_scheduler_functions
    mock_list.side_effect = Exception("Failed to retrieve jobs")

    result = await list_scheduled_tasks_tool()

    mock_list.assert_called_once_with()
    assert result == []
    assert "Error listing scheduled jobs" in caplog.text
    assert "Failed to retrieve jobs" in caplog.text

import pytest
import logging
from unittest.mock import patch, MagicMock, PropertyMock
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore # 타입 비교 위해 추가
import pytz # timezone 비교 위해 추가

# 테스트 대상 모듈 임포트 (정상 임포트)
from app.scheduler import config as scheduler_config
from app.scheduler import scheduler as scheduler_module
from app.scheduler import tasks as scheduler_tasks

# 로거 비활성화 (테스트 출력 깔끔하게)
logging.disable(logging.CRITICAL)

# --- Fixtures (필요 시 추가) ---

# reset_scheduler_mock fixture 제거

# --- Test Cases ---

def test_scheduler_config_loading():
    """스케줄러 설정 변수들이 올바르게 로드되는지 테스트"""
    assert isinstance(scheduler_config.SCHEDULER_SETTINGS, dict)
    assert isinstance(scheduler_config.SCHEDULE_CONFIG, dict)
    assert isinstance(scheduler_config.SOURCE_CONFIG, dict)

    # 필수 설정 키 확인 (예시)
    assert 'apscheduler.jobstores.default' in scheduler_config.SCHEDULER_SETTINGS
    assert 'apscheduler.executors.default' in scheduler_config.SCHEDULER_SETTINGS
    assert 'apscheduler.timezone' in scheduler_config.SCHEDULER_SETTINGS

    # SCHEDULE_CONFIG 내용 확인 (일부)
    assert 'research_blogs' in scheduler_config.SCHEDULE_CONFIG
    assert isinstance(scheduler_config.SCHEDULE_CONFIG['research_blogs']['trigger'], CronTrigger)

    # SOURCE_CONFIG 내용 확인 (일부)
    assert 'https://openai.com/blog/' in scheduler_config.SOURCE_CONFIG
    source_info = scheduler_config.SOURCE_CONFIG['https://openai.com/blog/']
    assert 'schedule_type' in source_info
    assert 'priority' in source_info

def test_scheduler_initialization():
    """BackgroundScheduler 인스턴스가 설정에 따라 초기화되는지 테스트 (단순화)"""
    try:
        # 실제 생성된 인스턴스 사용 (scheduler.py에서 생성됨)
        scheduler_instance = scheduler_module.scheduler
        assert isinstance(scheduler_instance, BackgroundScheduler)
        # 추가적으로 timezone 정도만 확인
        assert str(scheduler_instance.timezone) == scheduler_config.SCHEDULER_SETTINGS['apscheduler.timezone']
    except Exception as e:
        pytest.fail(f"Scheduler initialization failed: {e}")

@patch.object(scheduler_module.scheduler, 'add_job')
def test_add_collection_jobs(mock_add_job):
    """add_collection_jobs 함수가 설정을 기반으로 작업을 올바르게 추가하는지 테스트"""
    scheduler_module.scheduler.remove_all_jobs()
    scheduler_module.add_collection_jobs()

    expected_calls = len(scheduler_config.SOURCE_CONFIG)
    assert mock_add_job.call_count == expected_calls

    # 첫 번째 소스에 대한 호출 인자 확인 (예시)
    first_url = list(scheduler_config.SOURCE_CONFIG.keys())[0]
    first_config = scheduler_config.SOURCE_CONFIG[first_url]
    expected_schedule_type = first_config['schedule_type']
    expected_priority = first_config['priority']
    expected_trigger = scheduler_config.SCHEDULE_CONFIG[expected_schedule_type]['trigger']
    expected_job_id = f"collect_{first_url}"
    expected_name = f"Collect data from {first_url}"

    mock_add_job.assert_any_call(
        scheduler_tasks.collect_data_task,
        trigger=expected_trigger,
        args=[first_url, expected_priority],
        id=expected_job_id,
        name=expected_name,
        replace_existing=True
    )

@patch('app.scheduler.scheduler.logger')
@patch.object(scheduler_module.scheduler, 'add_job')
def test_add_collection_jobs_invalid_config(mock_add_job, mock_logger):
    """add_collection_jobs 함수가 잘못된 설정을 처리하는지 테스트"""
    # 테스트 전 job 상태 초기화 (선택적이지만 권장)
    scheduler_module.scheduler.remove_all_jobs()
    original_source_config = scheduler_config.SOURCE_CONFIG.copy()
    scheduler_config.SOURCE_CONFIG['invalid_url'] = {'schedule_type': 'invalid_type', 'priority': 1}

    try:
        scheduler_module.add_collection_jobs()
        expected_valid_calls = len(original_source_config)
        assert mock_add_job.call_count == expected_valid_calls
        mock_logger.warning.assert_called_once()
    finally:
        scheduler_config.SOURCE_CONFIG = original_source_config
        scheduler_module.scheduler.remove_all_jobs() # 테스트 후 정리

def test_start_scheduler():
    """start_scheduler 함수 로직 테스트 (scheduler 모킹)"""
    # Case 1: scheduler.running is False
    with patch('app.scheduler.scheduler.scheduler') as mock_scheduler, \
         patch('app.scheduler.scheduler.add_collection_jobs') as mock_add_jobs:
        mock_scheduler.running = False  # Mock 객체의 running 속성 설정
        scheduler_module.start_scheduler() # 내부적으로 mock_scheduler 사용
        mock_add_jobs.assert_called_once()
        mock_scheduler.start.assert_called_once()

    # Case 2: scheduler.running is True
    with patch('app.scheduler.scheduler.scheduler') as mock_scheduler, \
         patch('app.scheduler.scheduler.add_collection_jobs') as mock_add_jobs:
        mock_scheduler.running = True # Mock 객체의 running 속성 설정
        scheduler_module.start_scheduler()
        mock_add_jobs.assert_not_called()
        mock_scheduler.start.assert_not_called()

def test_stop_scheduler():
    """stop_scheduler 함수 로직 테스트 (scheduler 모킹)"""
    # Case 1: scheduler.running is True
    with patch('app.scheduler.scheduler.scheduler') as mock_scheduler:
        mock_scheduler.running = True
        scheduler_module.stop_scheduler()
        mock_scheduler.shutdown.assert_called_once()

    # Case 2: scheduler.running is False
    with patch('app.scheduler.scheduler.scheduler') as mock_scheduler:
        mock_scheduler.running = False
        scheduler_module.stop_scheduler()
        mock_scheduler.shutdown.assert_not_called()


# --- FastAPI 연동 테스트 --- 
@pytest.mark.asyncio
@patch('app.main.start_scheduler')
@patch('app.main.stop_scheduler')
@patch('app.main.start_mcp_in_thread')
async def test_fastapi_lifespan(mock_start_mcp, mock_stop_scheduler, mock_start_scheduler):
    """FastAPI lifespan 이벤트가 스케줄러 시작/종료를 올바르게 호출하는지 테스트"""
    from app import main as main_app

    async with main_app.lifespan(main_app.app):
        mock_start_scheduler.assert_called_once()
        if main_app.MCP_ENABLED:
             mock_start_mcp.assert_called_once()
        else:
            mock_start_mcp.assert_not_called()
        mock_stop_scheduler.assert_not_called()

    mock_stop_scheduler.assert_called_once()


# --- 작업 실행 테스트 --- 

def test_determine_source_type():
    """determine_source_type 함수가 URL 유형을 올바르게 판단하는지 테스트"""
    assert scheduler_tasks.determine_source_type("http://example.com/rss.xml") == "rss"
    assert scheduler_tasks.determine_source_type("http://example.com/feed") == "rss"
    assert scheduler_tasks.determine_source_type("http://example.com/blog") == "web"
    assert scheduler_tasks.determine_source_type("http://example.com/news.html") == "web"

@patch('app.scheduler.tasks.logger.info')
@patch('app.scheduler.tasks.logger.error')
@patch('app.scheduler.tasks.determine_source_type', return_value='rss')
def test_collect_data_task_rss(mock_determine_type, mock_log_error, mock_log_info):
    """collect_data_task가 RSS 타입 소스를 처리하는지 테스트"""
    test_url = "http://example.com/rss.xml"
    test_priority = 1
    scheduler_tasks.collect_data_task(test_url, test_priority)
    
    mock_determine_type.assert_called_once_with(test_url)
    # 현재는 시뮬레이션 로그 확인
    mock_log_info.assert_any_call(f"Simulating RSS collection for: {test_url}")
    mock_log_error.assert_not_called()

@patch('app.scheduler.tasks.logger.info')
@patch('app.scheduler.tasks.logger.error')
@patch('app.scheduler.tasks.determine_source_type', return_value='web')
def test_collect_data_task_web(mock_determine_type, mock_log_error, mock_log_info):
    """collect_data_task가 Web 타입 소스를 처리하는지 테스트"""
    test_url = "http://example.com/blog"
    test_priority = 5
    scheduler_tasks.collect_data_task(test_url, test_priority)
    
    mock_determine_type.assert_called_once_with(test_url)
    # 현재는 시뮬레이션 로그 확인
    mock_log_info.assert_any_call(f"Simulating web crawling for: {test_url}")
    mock_log_error.assert_not_called()

@patch('app.scheduler.tasks.logger.error')
@patch('app.scheduler.tasks.determine_source_type', side_effect=Exception("Test error"))
def test_collect_data_task_exception(mock_determine_type, mock_log_error):
    """collect_data_task 실행 중 예외 발생 시 에러 로그 기록 테스트"""
    test_url = "http://error.com"
    test_priority = 3
    scheduler_tasks.collect_data_task(test_url, test_priority)
    
    mock_log_error.assert_called_once()
    # 에러 메시지 내용 검증 (선택적)
    # assert "Test error" in mock_log_error.call_args[0][0]

# --- 추가 테스트 케이스 작성 예정 --- 

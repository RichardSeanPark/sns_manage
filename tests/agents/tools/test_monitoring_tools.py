import pytest
from unittest.mock import patch, MagicMock

# 테스트 대상 도구 임포트
from app.agents.tools.monitoring_tools import (
    log_monitoring_start_tool,
    log_monitoring_end_tool,
    LogStartInput,
    LogEndInput
)
from app.models.enums import MonitoringStatus # 상태 Enum 임포트

# --- Fixtures ---

@pytest.fixture(autouse=True)
def patch_monitoring_store():
    """monitoring_store 객체를 모의 객체로 패치하는 fixture"""
    # 'app.agents.tools.monitoring_tools' 모듈 내의 monitoring_store를 패치
    with patch('app.agents.tools.monitoring_tools.monitoring_store', new_callable=MagicMock) as mock_store:
        # 각 테스트에서 구체적인 반환값 설정 가능하도록 mock_store 반환
        yield mock_store

# --- Tests for log_monitoring_start_tool ---

def test_log_start_success(patch_monitoring_store: MagicMock):
    """작업 시작 로그 기록 성공 및 log ID 반환 확인"""
    expected_log_id = 123
    patch_monitoring_store.log_start.return_value = expected_log_id
    task_name = "test_task_start"
    input_data = LogStartInput(task_name=task_name)

    result = log_monitoring_start_tool(input_data)

    patch_monitoring_store.log_start.assert_called_once_with(task_name)
    assert result == expected_log_id

def test_log_start_repo_returns_none(patch_monitoring_store: MagicMock, caplog):
    """저장소 log_start가 None 반환 시 None 반환 및 로그 확인"""
    patch_monitoring_store.log_start.return_value = None
    task_name = "failed_start_task"
    input_data = LogStartInput(task_name=task_name)

    result = log_monitoring_start_tool(input_data)

    patch_monitoring_store.log_start.assert_called_once_with(task_name)
    assert result is None
    assert f"Failed to start monitoring log for task '{task_name}'" in caplog.text

def test_log_start_repo_error(patch_monitoring_store: MagicMock, caplog):
    """저장소 log_start에서 예외 발생 시 None 반환 및 로그 확인"""
    error_message = "Database connection failed"
    patch_monitoring_store.log_start.side_effect = Exception(error_message)
    task_name = "error_start_task"
    input_data = LogStartInput(task_name=task_name)

    result = log_monitoring_start_tool(input_data)

    patch_monitoring_store.log_start.assert_called_once_with(task_name)
    assert result is None
    assert "Error in log_monitoring_start_tool" in caplog.text
    assert error_message in caplog.text

# --- Tests for log_monitoring_end_tool ---

@pytest.mark.parametrize("status_to_test", [MonitoringStatus.SUCCESS, MonitoringStatus.FAILED, MonitoringStatus.PARTIAL_SUCCESS])
def test_log_end_success(patch_monitoring_store: MagicMock, status_to_test: MonitoringStatus):
    """작업 종료 로그 기록 성공 (다양한 상태) 및 True 반환 확인"""
    patch_monitoring_store.log_end.return_value = True
    log_id = 456
    input_data = LogEndInput(
        log_id=log_id,
        status=status_to_test,
        items_processed=10,
        items_succeeded=8 if status_to_test != MonitoringStatus.FAILED else 0,
        items_failed=2 if status_to_test != MonitoringStatus.SUCCESS else 0,
        error_message="An error occurred" if status_to_test == MonitoringStatus.FAILED else None
    )

    result = log_monitoring_end_tool(input_data)

    patch_monitoring_store.log_end.assert_called_once_with(
        log_id=log_id,
        status=status_to_test,
        items_processed=input_data.items_processed,
        items_succeeded=input_data.items_succeeded,
        items_failed=input_data.items_failed,
        error_message=input_data.error_message,
        details=None # 기본값 확인
    )
    assert result is True

def test_log_end_repo_returns_false(patch_monitoring_store: MagicMock, caplog):
    """저장소 log_end가 False 반환 시 False 반환 및 로그 확인"""
    patch_monitoring_store.log_end.return_value = False
    log_id = 789
    input_data = LogEndInput(log_id=log_id, status=MonitoringStatus.SUCCESS)

    result = log_monitoring_end_tool(input_data)

    patch_monitoring_store.log_end.assert_called_once() # 호출 인자 검증은 test_log_end_success에서
    assert result is False
    assert f"Failed to end monitoring log for Log ID: {log_id}" in caplog.text

def test_log_end_repo_error(patch_monitoring_store: MagicMock, caplog):
    """저장소 log_end에서 예외 발생 시 False 반환 및 로그 확인"""
    error_message = "DB update error"
    patch_monitoring_store.log_end.side_effect = Exception(error_message)
    log_id = 101
    input_data = LogEndInput(log_id=log_id, status=MonitoringStatus.FAILED, error_message="Task failed")

    result = log_monitoring_end_tool(input_data)

    patch_monitoring_store.log_end.assert_called_once()
    assert result is False
    assert "Error in log_monitoring_end_tool" in caplog.text
    assert error_message in caplog.text

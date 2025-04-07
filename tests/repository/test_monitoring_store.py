import pytest
import os
import uuid
from datetime import datetime, timezone
from typing import Generator
from pathlib import Path

from sqlalchemy import create_engine, inspect as sqlalchemy_inspect
from sqlalchemy.orm import sessionmaker, Session

from app.repository.monitoring_store import SQLiteMonitoringRepository
from app.models.db_models import Base, MonitoringLogDB
from app.models.enums import MonitoringStatus
from app.config import BASE_DIR

# --- Test Setup (Reusing concepts from test_sqlite_store) ---

# 임시 테스트 데이터베이스 경로 설정
TEST_DB_DIR = BASE_DIR / "tests" / "temp_data"

@pytest.fixture(scope="session", autouse=True)
def setup_test_db_directory():
    """테스트 시작 전 임시 데이터 디렉토리 생성"""
    TEST_DB_DIR.mkdir(parents=True, exist_ok=True)
    yield

@pytest.fixture(scope="function")
def db_engine_session():
    """각 테스트 함수마다 독립적인 DB 엔진과 세션 생성"""
    db_path = TEST_DB_DIR / f"test_monitoring_db_{uuid.uuid4()}.db"
    test_db_url = f"sqlite:///{db_path}"
    
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    # Base에 MonitoringLogDB가 포함되어 있으므로 모든 테이블 생성
    Base.metadata.create_all(bind=engine) 
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield engine, SessionLocal

    # 테스트 함수 종료 후 DB 파일 삭제
    if db_path.exists():
        os.remove(db_path)

@pytest.fixture(scope="function")
def monitoring_repo(db_engine_session) -> SQLiteMonitoringRepository:
    """각 테스트 함수를 위한 SQLiteMonitoringRepository 인스턴스 생성"""
    engine, SessionLocal = db_engine_session
    
    repo = SQLiteMonitoringRepository(db_url=str(engine.url))
    repo.engine = engine
    repo.SessionLocal = SessionLocal
    
    # 테이블 비우기 (각 테스트 시작 시)
    with repo.get_db() as db:
        db.query(MonitoringLogDB).delete()
        db.commit()
        
    return repo

# --- Test Cases ---

def test_log_start_success(monitoring_repo: SQLiteMonitoringRepository):
    """log_start 성공 테스트"""
    task_name = "test_task_start"
    log_id = monitoring_repo.log_start(task_name)
    
    assert log_id is not None
    assert isinstance(log_id, int)
    
    # DB 직접 확인
    with monitoring_repo.get_db() as db:
        log_entry = db.get(MonitoringLogDB, log_id)
        assert log_entry is not None
        assert log_entry.id == log_id
        assert log_entry.task_name == task_name
        assert log_entry.status == MonitoringStatus.STARTED.value
        assert log_entry.start_time is not None
        assert log_entry.end_time is None
        assert log_entry.error_message is None

def test_log_end_success(monitoring_repo: SQLiteMonitoringRepository):
    """log_end 성공 테스트 (성공 상태)"""
    task_name = "test_task_end_success"
    log_id = monitoring_repo.log_start(task_name)
    assert log_id is not None
    
    items_processed = 100
    items_succeeded = 95
    items_failed = 5
    details = {"info": "Completed successfully with minor failures"}
    
    success = monitoring_repo.log_end(
        log_id=log_id,
        status=MonitoringStatus.PARTIAL_SUCCESS,
        items_processed=items_processed,
        items_succeeded=items_succeeded,
        items_failed=items_failed,
        details=details
    )
    
    assert success is True
    
    # DB 직접 확인
    with monitoring_repo.get_db() as db:
        log_entry = db.get(MonitoringLogDB, log_id)
        assert log_entry is not None
        assert log_entry.status == MonitoringStatus.PARTIAL_SUCCESS.value
        assert log_entry.end_time is not None
        assert log_entry.start_time < log_entry.end_time
        assert log_entry.items_processed == items_processed
        assert log_entry.items_succeeded == items_succeeded
        assert log_entry.items_failed == items_failed
        assert log_entry.error_message is None
        assert log_entry.details == details

def test_log_end_with_error(monitoring_repo: SQLiteMonitoringRepository):
    """log_end 성공 테스트 (실패 상태 및 오류 메시지 포함)"""
    task_name = "test_task_end_failure"
    log_id = monitoring_repo.log_start(task_name)
    assert log_id is not None

    error_msg = "Critical failure during processing."
    details = {"failed_urls": ["url1", "url2"]}
    
    success = monitoring_repo.log_end(
        log_id=log_id,
        status=MonitoringStatus.FAILED,
        error_message=error_msg,
        details=details,
        items_processed=10, # 예시 값
        items_failed=10
    )
    
    assert success is True
    
    # DB 직접 확인
    with monitoring_repo.get_db() as db:
        log_entry = db.get(MonitoringLogDB, log_id)
        assert log_entry is not None
        assert log_entry.status == MonitoringStatus.FAILED.value
        assert log_entry.end_time is not None
        assert log_entry.error_message == error_msg
        assert log_entry.details == details
        assert log_entry.items_failed == 10

def test_log_end_not_found(monitoring_repo: SQLiteMonitoringRepository):
    """존재하지 않는 로그 ID 업데이트 시 실패 확인"""
    non_existent_log_id = 9999
    success = monitoring_repo.log_end(non_existent_log_id, MonitoringStatus.SUCCESS)
    assert success is False

def test_log_end_invalid_status_type(monitoring_repo: SQLiteMonitoringRepository):
    """잘못된 status 타입으로 log_end 호출 시 실패 확인"""
    task_name = "test_invalid_status"
    log_id = monitoring_repo.log_start(task_name)
    assert log_id is not None

    # MonitoringStatus Enum이 아닌 문자열 전달
    success = monitoring_repo.log_end(log_id, "invalid_status_string") 
    assert success is False

    # DB 확인 (상태가 업데이트되지 않았는지)
    with monitoring_repo.get_db() as db:
        log_entry = db.get(MonitoringLogDB, log_id)
        assert log_entry is not None
        # 여전히 STARTED 상태여야 함
        assert log_entry.status == MonitoringStatus.STARTED.value
        assert log_entry.end_time is None # end_time도 업데이트 안됨 
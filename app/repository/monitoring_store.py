import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from sqlalchemy import create_engine, update
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.db_models import MonitoringLogDB, Base
from app.models.enums import MonitoringStatus
from app.config import DATABASE_URL, DB_CONNECT_ARGS
from contextlib import contextmanager
import inspect as sqlalchemy_inspect # inspect 이름 충돌 방지

logger = logging.getLogger(__name__)

class SQLiteMonitoringRepository:
    """모니터링 로그를 SQLite 데이터베이스에 저장하고 관리하는 저장소"""

    def __init__(self, db_url: str = DATABASE_URL, connect_args: dict = None):
        if connect_args is None:
            connect_args = DB_CONNECT_ARGS
        try:
            self.engine = create_engine(db_url, connect_args=connect_args)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            # 테이블 생성은 주 저장소 또는 앱 초기화 시 처리하는 것이 일반적
            # self._create_monitoring_table()
            logger.info(f"SQLiteMonitoringRepository initialized with db: {db_url}")
        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize SQLiteMonitoringRepository: {e}", exc_info=True)
            raise

    # 테이블 생성 로직은 앱 초기화 또는 다른 저장소에서 관리하는 것으로 가정
    # def _create_monitoring_table(self):
    #     try:
    #         inspector = sqlalchemy_inspect(self.engine)
    #         if not inspector.has_table(MonitoringLogDB.__tablename__):
    #             Base.metadata.create_all(bind=self.engine, tables=[MonitoringLogDB.__table__])
    #             logger.info(f"Table '{MonitoringLogDB.__tablename__}' created.")
    #         else:
    #             logger.info(f"Table '{MonitoringLogDB.__tablename__}' already exists.")
    #     except SQLAlchemyError as e:
    #         logger.error(f"Failed to create monitoring table: {e}", exc_info=True)

    @contextmanager
    def get_db(self) -> Session:
        """데이터베이스 세션 컨텍스트 관리자"""
        db = self.SessionLocal()
        try:
            yield db
        except SQLAlchemyError as e:
            logger.error(f"Monitoring DB session error: {e}", exc_info=True)
            db.rollback()
            raise
        finally:
            db.close()

    def log_start(self, task_name: str) -> Optional[int]:
        """작업 시작 로그를 기록하고 로그 ID를 반환합니다."""
        log_entry = MonitoringLogDB(
            task_name=task_name,
            status=MonitoringStatus.STARTED.value
            # start_time은 DB 기본값으로 설정됨
        )
        try:
            with self.get_db() as db:
                db.add(log_entry)
                db.commit()
                db.refresh(log_entry) # 자동 생성된 ID 및 start_time 로드
                logger.info(f"Monitoring task '{task_name}' started. Log ID: {log_entry.id}")
                return log_entry.id
        except SQLAlchemyError as e:
            logger.error(f"Failed to log start for task '{task_name}': {e}", exc_info=True)
            return None

    def log_end(
        self,
        log_id: int,
        status: MonitoringStatus,
        items_processed: Optional[int] = None,
        items_succeeded: Optional[int] = None,
        items_failed: Optional[int] = None,
        error_message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """작업 종료 로그 (상태, 통계, 오류 등)를 업데이트합니다."""
        if not isinstance(status, MonitoringStatus):
            logger.error(f"Invalid status type provided for log_end: {type(status)}")
            return False
            
        update_values = {
            "end_time": datetime.now(timezone.utc),
            "status": status.value,
            "items_processed": items_processed,
            "items_succeeded": items_succeeded,
            "items_failed": items_failed,
            "error_message": error_message,
            "details": details
        }
        # None 값은 업데이트에서 제외 (선택적, DB 기본값 유지 또는 기존 값 유지 위함)
        update_values = {k: v for k, v in update_values.items() if v is not None}

        try:
            with self.get_db() as db:
                stmt = (
                    update(MonitoringLogDB)
                    .where(MonitoringLogDB.id == log_id)
                    .values(**update_values)
                )
                result = db.execute(stmt)
                db.commit()
                if result.rowcount == 0:
                    logger.warning(f"No monitoring log found with ID {log_id} to update.")
                    return False
                logger.info(f"Monitoring log ID {log_id} updated with status: {status.value}")
                return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to update monitoring log ID {log_id}: {e}", exc_info=True)
            return False

# 모니터링 저장소 인스턴스 (필요에 따라 싱글톤 또는 DI 사용)
monitoring_store = SQLiteMonitoringRepository() 
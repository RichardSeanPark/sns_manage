import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

# agents 임포트 시도
try:
    from agents import tool
except ImportError:
    # 대체 데코레이터 정의
    def tool(func):
        return func
    logger = logging.getLogger(__name__)
    logger.warning("Could not import 'agents' library. Using dummy 'tool' decorator.")

from app.repository.monitoring_store import monitoring_store # 모니터링 저장소 인스턴스 직접 임포트
from app.models.enums import MonitoringStatus # 모니터링 상태 Enum

logger = logging.getLogger(__name__)

# --- Log Monitoring Start Tool ---

class LogStartInput(BaseModel):
    task_name: str = Field(description="시작하는 작업의 이름")
    # 필요에 따라 추가 컨텍스트 정보 필드 추가 가능
    # context_data: Optional[Dict[str, Any]] = Field(default=None, description="작업 시작 관련 추가 정보")

@tool
def log_monitoring_start_tool(input_data: LogStartInput) -> Optional[int]:
    """
    모니터링 시스템에 특정 작업의 시작을 기록합니다.
    성공 시 로그 ID (정수)를 반환하고, 실패 시 None을 반환합니다.
    """
    logger.info(f"Tool 'log_monitoring_start_tool' called for task: {input_data.task_name}")
    try:
        log_id = monitoring_store.log_start(input_data.task_name)
        if log_id is not None:
            logger.info(f"Monitoring log started for task '{input_data.task_name}' with Log ID: {log_id}")
            return log_id
        else:
            logger.error(f"Failed to start monitoring log for task '{input_data.task_name}'.")
            return None
    except Exception as e:
        logger.error(f"Error in log_monitoring_start_tool: {e}", exc_info=True)
        return None

# --- Log Monitoring End Tool ---

class LogEndInput(BaseModel):
    log_id: int = Field(description="종료할 모니터링 로그의 ID")
    status: MonitoringStatus = Field(description="작업의 최종 상태 (SUCCESS, FAILED, PARTIAL_SUCCESS)")
    items_processed: Optional[int] = Field(default=None, description="처리된 총 아이템 수")
    items_succeeded: Optional[int] = Field(default=None, description="성공적으로 처리된 아이템 수")
    items_failed: Optional[int] = Field(default=None, description="실패하거나 스킵된 아이템 수")
    error_message: Optional[str] = Field(default=None, description="작업 실패 시 오류 메시지")
    details: Optional[Dict[str, Any]] = Field(default=None, description="추가 상세 정보 (JSON 호환)")

@tool
def log_monitoring_end_tool(input_data: LogEndInput) -> bool:
    """
    모니터링 시스템에 특정 작업의 종료 상태 및 결과를 기록합니다.
    성공 시 True, 실패 시 False를 반환합니다.
    """
    logger.info(f"Tool 'log_monitoring_end_tool' called for Log ID: {input_data.log_id} with status: {input_data.status}")
    try:
        success = monitoring_store.log_end(
            log_id=input_data.log_id,
            status=input_data.status,
            items_processed=input_data.items_processed,
            items_succeeded=input_data.items_succeeded,
            items_failed=input_data.items_failed,
            error_message=input_data.error_message,
            details=input_data.details
        )
        if success:
            logger.info(f"Monitoring log ended successfully for Log ID: {input_data.log_id}")
        else:
            logger.warning(f"Failed to end monitoring log for Log ID: {input_data.log_id} (e.g., log ID not found or invalid status).")
        return success
    except Exception as e:
        logger.error(f"Error in log_monitoring_end_tool: {e}", exc_info=True)
        return False

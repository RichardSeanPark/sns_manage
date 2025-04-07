from enum import Enum

class SourceType(str, Enum):
    """데이터 소스 유형"""
    RSS = "rss"
    CRAWLING = "crawling"
    API = "api"
    UNKNOWN = "unknown"

class ProcessingStatus(str, Enum):
    """데이터 처리 상태"""
    PENDING = "pending"        # 처리 대기 중
    RAW = "raw"                # 원시 데이터 (수집 직후)
    FILTERED = "filtered"      # 기본 필터링 완료
    SUMMARIZING = "summarizing"  # 요약 중
    SUMMARIZED = "summarized"    # 요약 완료
    ANALYZING = "analyzing"    # 분석 중
    ANALYZED = "analyzed"      # 분석 완료
    PUBLISHING = "publishing"  # 게시 중
    PUBLISHED = "published"      # 게시 완료
    ERROR = "error"            # 처리 중 오류 발생
    SKIPPED = "skipped"        # 처리 건너뜀 (e.g., 중복)

class MonitoringStatus(str, Enum):
    """모니터링 작업 상태"""
    STARTED = "started"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL_SUCCESS = "partial_success" # 일부 성공, 일부 실패
    SKIPPED = "skipped" # 실행 조건 미충족 등으로 건너뜀 
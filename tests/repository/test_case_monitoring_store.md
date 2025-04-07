# SQLiteMonitoringRepository 테스트 계획

이 문서는 `app.repository.monitoring_store.SQLiteMonitoringRepository` 클래스의 기능 검증을 위한 테스트 계획 및 진행 상황을 기록합니다.

## 기능: 모니터링 로그 관리

- [x] 모니터링 상태 Enum 정의 (`app/models/enums.py`)
- [x] 모니터링 로그 DB 모델 정의 (`app/models/db_models.py`)
- [x] `SQLiteMonitoringRepository` 구현 (`app/repository/monitoring_store.py`)
    - [x] 작업 시작 로그 기록 (`log_start`)
    - [x] 작업 종료 로그 업데이트 (`log_end`)
- [x] RSS 수집 태스크에 모니터링 로깅 통합 (`app/scheduler/tasks.py`)

## 테스트: SQLiteMonitoringRepository

- [x] `test_log_start_success`: 작업 시작 로그가 성공적으로 기록되고 올바른 ID를 반환하는지 확인
    - [x] 반환된 ID가 정수형인지 확인
    - [x] DB에 해당 ID로 로그가 생성되었는지 확인
    - [x] 생성된 로그의 `task_name`, `status` (STARTED), `start_time`이 올바른지 확인
    - [x] `end_time`, `error_message` 등이 초기 상태(None)인지 확인
- [x] `test_log_end_success`: 작업 종료 로그 업데이트 (성공/부분 성공 상태)가 성공적으로 이루어지는지 확인
    - [x] `log_end` 호출이 `True`를 반환하는지 확인
    - [x] DB에서 해당 로그를 조회하여 상태(`status`), `end_time`, 통계(`items_processed`, `items_succeeded`, `items_failed`), 상세 정보(`details`)가 올바르게 업데이트되었는지 확인
    - [x] `error_message`가 `None`으로 유지되는지 확인
- [x] `test_log_end_with_error`: 작업 종료 로그 업데이트 (실패 상태) 및 오류 메시지 기록이 성공적으로 이루어지는지 확인
    - [x] `log_end` 호출이 `True`를 반환하는지 확인
    - [x] DB에서 해당 로그를 조회하여 상태(`status` FAILED), `end_time`, 오류 메시지(`error_message`), 상세 정보(`details`), 관련 통계가 올바르게 업데이트되었는지 확인
- [x] `test_log_end_not_found`: 존재하지 않는 로그 ID로 `log_end` 호출 시 `False`를 반환하는지 확인
- [x] `test_log_end_invalid_status_type`: 잘못된 타입(Enum 아님)의 `status`로 `log_end` 호출 시 `False`를 반환하고 DB가 업데이트되지 않는지 확인 
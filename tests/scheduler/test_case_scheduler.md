# 스케줄러 모듈 테스트 계획

## 태스크: 데이터 수집 작업 스케줄러 구현

- [x] `APScheduler` 의존성 추가 (`requirements.txt`)
- [x] 스케줄러 모듈 구조 생성 (`app/scheduler/`)
- [x] 사이트별 스케줄 설정 및 우선순위 정의 (`app/scheduler/config.py`)
- [x] 스케줄러 초기화 및 작업 추가 로직 구현 (`app/scheduler/scheduler.py`)
- [x] 데이터 수집 작업 함수 기본 구조 구현 (`app.scheduler.tasks.py`)
- [x] FastAPI `lifespan` 연동 (`app/main.py`)

## 테스트: 스케줄러 모듈

- [x] 설정 로드 테스트 (`test_scheduler_config_loading`)
    - [x] `SCHEDULER_SETTINGS`, `SCHEDULE_CONFIG`, `SOURCE_CONFIG` 변수 타입 및 기본 키 확인
- [x] 스케줄러 초기화 테스트 (`test_scheduler_initialization`)
    - [x] `BackgroundScheduler` 인스턴스 생성 확인
    - [x] 설정된 timezone 확인
    - [x] 기본 jobstore 설정 확인 (`_jobstores` 접근)
- [x] 작업 추가 테스트 (`test_add_collection_jobs`)
    - [x] 설정 기반 `add_job` 호출 횟수 확인
    - [x] `add_job` 호출 시 인자(작업 함수, 트리거, args, id, name, replace_existing) 확인
- [x] 작업 추가 - 잘못된 설정 테스트 (`test_add_collection_jobs_invalid_config`)
    - [x] 유효한 작업만 추가되는지 확인
    - [x] 경고 로그 발생 확인
- [x] 스케줄러 시작 테스트 (`test_start_scheduler`)
    - [x] `running=False`일 때 `add_collection_jobs`, `scheduler.start` 호출 확인
    - [x] `running=True`일 때 `add_collection_jobs`, `scheduler.start` 미호출 확인
- [x] 스케줄러 중지 테스트 (`test_stop_scheduler`)
    - [x] `running=True`일 때 `scheduler.shutdown` 호출 확인
    - [x] `running=False`일 때 `scheduler.shutdown` 미호출 확인
- [x] FastAPI 연동 테스트 (`test_fastapi_lifespan`)
    - [x] 앱 시작 시 `start_scheduler` 호출 확인
    - [x] 앱 종료 시 `stop_scheduler` 호출 확인
- [x] 소스 유형 결정 함수 테스트 (`test_determine_source_type`)
    - [x] URL 기반 'rss'/'web' 반환 확인
- [x] 데이터 수집 작업 함수 테스트 - RSS (`test_collect_data_task_rss`)
    - [x] `determine_source_type` 호출 확인
    - [x] 관련 로그 확인 (시뮬레이션)
    - [x] 에러 로그 미발생 확인
- [x] 데이터 수집 작업 함수 테스트 - Web (`test_collect_data_task_web`)
    - [x] `determine_source_type` 호출 확인
    - [x] 관련 로그 확인 (시뮬레이션)
    - [x] 에러 로그 미발생 확인
- [x] 데이터 수집 작업 함수 테스트 - 예외 (`test_collect_data_task_exception`)
    - [x] 예외 발생 시 에러 로그 확인 
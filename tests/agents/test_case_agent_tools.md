# 에이전트 도구 (Agent Tools) 테스트 계획

이 문서는 Collector Agent가 사용하는 개별 도구들의 기능 검증을 위한 테스트 계획 및 진행 상황을 기록합니다.

## 1. 데이터 관리 도구 (`app.agents.tools.data_management_tools`)

### 기능: `get_collected_data_tool`
- [x] 저장소에서 데이터 조회 (필터링 및 페이지네이션)

### 테스트: `get_collected_data_tool`
- [x] `test_get_data_no_query`: 쿼리 없이 호출 시 모든 데이터 반환 (페이지네이션 적용) 확인
- [x] `test_get_data_with_query`: 특정 쿼리 조건으로 호출 시 필터링된 데이터 반환 확인
- [x] `test_get_data_pagination`: `skip`, `limit` 파라미터 동작 확인
- [x] `test_get_data_empty_result`: 조회 결과가 없을 때 빈 리스트 반환 확인
- [x] `test_get_data_repository_error`: 저장소 오류 발생 시 빈 리스트 반환 확인 (오류 로깅 확인)

### 기능: `save_collected_data_tool`
- [x] 단일 `CollectedData` 객체를 저장소에 저장 (중복 체크 포함)

### 테스트: `save_collected_data_tool`
- [x] `test_save_data_success`: 새로운 데이터 저장 성공 및 저장된 객체 반환 확인
- [x] `test_save_data_duplicate`: 중복 데이터 저장 시도 시 `None` 반환 확인 (또는 정책에 따른 동작 확인)
- [ ] `test_save_data_invalid_data`: 유효하지 않은 데이터 입력 시 오류 처리 확인 (예: Pydantic 유효성 검사)
- [x] `test_save_data_repository_error`: 저장소 오류 발생 시 `None` 반환 확인 (오류 로깅 확인)

## 2. 데이터 수집 도구 (`app.agents.tools.collection_tools`)

### 기능: `collect_rss_feeds_tool`
- [x] 지정된 URL 또는 모든 설정된 URL의 RSS 피드를 비동기적으로 파싱하여 `CollectedData` 리스트 반환

### 테스트: `collect_rss_feeds_tool`
- [x] `test_collect_rss_specific_urls`: 특정 URL 목록 입력 시 해당 피드만 파싱하는지 확인
- [x] `test_collect_rss_all_urls`: 입력 URL 없이 호출 시 설정된 모든 피드 파싱 시도 확인
- [ ] `test_collect_rss_valid_feed`: 유효한 RSS 피드로부터 `CollectedData` 객체가 정상적으로 생성되는지 확인 (필드 값 검증)
- [ ] `test_collect_rss_invalid_feed_url`: 잘못된 URL 입력 시 빈 리스트 반환 및 오류 로깅 확인
- [ ] `test_collect_rss_illformed_feed`: 형식이 잘못된 피드 처리 확인 (bozo=1)
- [ ] `test_collect_rss_empty_feed`: 항목이 없는 피드 처리 확인 (빈 리스트 반환)
- [x] `test_collect_rss_partial_failure`: 여러 URL 중 일부만 실패 시, 성공한 피드의 결과만 반환하는지 확인

### 기능: `crawl_webpage_tool`
- [x] 주어진 URL의 웹 페이지를 크롤링하여 제목, 본문 등을 추출하고 `CollectedData` 객체 반환

### 테스트: `crawl_webpage_tool`
- [x] `test_crawl_valid_page`: 유효한 URL 입력 시 `CollectedData` 객체 정상 반환 확인 (제목, 콘텐츠 일부 검증)
- [x] `test_crawl_invalid_url`: 잘못된 URL 입력 시 `None` 반환 및 오류 로깅 확인 (HTTP 오류, 요청 오류 등)
- [ ] `test_crawl_page_no_title`: 제목 태그가 없는 페이지 처리 확인 (URL을 제목으로 사용)
- [ ] `test_crawl_page_no_content`: 주요 콘텐츠 추출 실패 시 처리 확인 (빈 콘텐츠 또는 None 반환 등 정책 확인)

## 3. 스케줄러 도구 (`app.agents.tools.scheduler_tools`)

### 기능: `schedule_collection_task_tool`
- [x] 함수 경로와 트리거 정보를 받아 스케줄러에 작업 추가

### 테스트: `schedule_collection_task_tool`
- [x] `test_schedule_interval_job`: `interval` 트리거로 작업 추가 성공 및 job ID 반환 확인
- [x] `test_schedule_cron_job`: `cron` 트리거로 작업 추가 성공 및 job ID 반환 확인
- [ ] `test_schedule_with_id_name`: `job_id`, `job_name` 지정하여 작업 추가 확인
- [ ] `test_schedule_replace_existing`: `replace_existing=True` 동작 확인
- [x] `test_schedule_invalid_function_path`: 잘못된 함수 경로 입력 시 `None` 반환 및 오류 로깅 확인
- [x] `test_schedule_invalid_trigger`: 잘못된 트리거 정보 입력 시 `None` 반환 및 오류 로깅 확인
- [x] `test_schedule_scheduler_add_error`: 스케줄러 작업 추가 실패 시 `None` 반환 및 오류 로깅 확인

### 기능: `check_task_status_tool`
- [x] Job ID로 스케줄된 작업 상태 조회

### 테스트: `check_task_status_tool`
- [x] `test_check_existing_job`: 존재하는 job ID 조회 시 `JobStatus` 객체 반환 확인 (필드 값 검증)
- [x] `test_check_nonexistent_job`: 존재하지 않는 job ID 조회 시 `None` 반환 확인
- [x] `test_check_job_scheduler_error`: 스케줄러 조회 오류 발생 시 `None` 반환 및 로그 기록 확인

### 기능: `list_scheduled_tasks_tool`
- [x] 현재 스케줄된 모든 작업 목록 조회

### 테스트: `list_scheduled_tasks_tool`
- [x] `test_list_jobs_empty`: 스케줄된 작업이 없을 때 빈 리스트 반환 확인
- [x] `test_list_jobs_multiple`: 여러 작업이 스케줄된 상태에서 올바른 목록 반환 확인
- [x] `test_list_jobs_scheduler_error`: 스케줄러 목록 조회 오류 시 빈 리스트 반환 및 로그 기록 확인

## 4. 모니터링 도구 (`app.agents.tools.monitoring_tools`)

### 기능: `log_monitoring_start_tool`
- [x] 작업 시작 로그 기록 및 log ID 반환

### 테스트: `log_monitoring_start_tool`
- [x] `test_log_start_success`: 작업 시작 로그 기록 성공 및 유효한 log ID (정수) 반환 확인
- [x] `test_log_start_repo_returns_none`: 저장소가 None을 반환할 때 처리 확인
- [x] `test_log_start_repo_error`: 저장소 오류 발생 시 `None` 반환 및 오류 로깅 확인

### 기능: `log_monitoring_end_tool`
- [x] 작업 종료 로그 기록 (상태, 통계, 오류 메시지 등)

### 테스트: `log_monitoring_end_tool`
- [x] `test_log_end_success`: `SUCCESS`, `PARTIAL_SUCCESS`, `FAILED` 등 다양한 상태로 종료 로그 기록 성공 (`True` 반환) 확인
- [x] `test_log_end_repo_returns_false`: 저장소가 False를 반환할 때 처리 확인
- [x] `test_log_end_repo_error`: 저장소 오류 발생 시 `False` 반환 및 오류 로깅 확인
- [ ] `test_log_end_invalid_log_id`: 존재하지 않는 log ID 입력 시 `False` 반환 확인

## 5. 평가 도구 (`app.agents.tools.evaluation_tools`)

### 기능: `evaluate_source_quality_tool`
- [x] 데이터 소스 URL의 품질 평가 (현재 임시 구현)

### 테스트: `evaluate_source_quality_tool` (임시 구현 기준)
- [x] `test_evaluate_returns_result`: 유효한 URL 입력 시 `EvaluationResult` 객체 반환 확인
- [x] `test_evaluate_score_is_rounded`: 반환된 점수가 소수점 둘째 자리로 반올림되는지 확인 (범위 0.0 ~ 1.0)

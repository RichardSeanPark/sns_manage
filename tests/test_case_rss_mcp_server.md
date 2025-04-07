# RSS-MCP 서버 테스트 케이스

이 문서는 RSS-MCP 서버의 테스트 케이스를 정의합니다.

## 1. MCP 서버 기본 구조 설계 테스트 (FastAPI 연동 포함)

- **TC-MCP-001: FastAPI 서버 루트 응답 테스트 (`test_fastapi_server`)**
  - **목표**: FastAPI 서버가 정상적으로 실행되고 루트 경로(`/`)에 응답하는지 확인합니다.
  - **상태**: [x] 통과 [ ] 실패 [ ] 보류
- **TC-MCP-002: Health Check 엔드포인트 테스트 (`test_health_endpoint`)**
  - **목표**: `/health` 엔드포인트가 정상적으로 상태(`{"status": "healthy"}`)를 반환하는지 확인합니다.
  - **상태**: [x] 통과 [ ] 실패 [ ] 보류
- **TC-MCP-003: API 상태 엔드포인트 테스트 (`test_api_status`)**
  - **목표**: `/api/status` 엔드포인트가 서버 상태 및 버전 정보를 포함한 JSON을 반환하는지 확인합니다.
  - **상태**: [x] 통과 [ ] 실패 [ ] 보류
- **TC-MCP-004: MCP 서버 시작 이벤트 테스트 (`setUpClass`)**
  - **목표**: FastAPI 시작 시 `startup_event`가 호출되어 MCP 서버가 별도 스레드에서 실행되는지 간접적으로 확인합니다. (MCP 앱 인스턴스 로딩 및 다른 테스트 성공 여부로 판단)
  - **상태**: [x] 통과 [ ] 실패 [ ] 보류

## 2. RSS 피드 관련 MCP 도구 구현 테스트

- **TC-MCP-005: MCP 도구 등록 확인 (`test_mcp_server_tools`)**
  - **목표**: 필요한 MCP 도구(`collect_rss_feeds_tool`, `get_latest_feeds_tool`, `search_feeds_tool`, 요약/음성 도구 등)가 MCP 앱에 모두 등록되었는지 확인합니다.
  - **상태**: [x] 통과 [ ] 실패 [ ] 보류
- **TC-MCP-006: 피드 수집 도구 엔드포인트 테스트 (`test_collect_feeds`)**
  - **목표**: `/api/feeds/collect` POST 요청 시 피드 수집 기능이 호출되고, 결과 메시지와 수집된 피드 수를 반환하는지 확인합니다.
  - **상태**: [x] 통과 [ ] 실패 [ ] 보류
- **TC-MCP-007: 최신 피드 조회 도구 엔드포인트 테스트 (`test_latest_feeds`)**
  - **목표**: `/api/feeds/latest` GET 요청 시 최신 피드 목록을 JSON 형태로 반환하는지 확인합니다. (결과 구조 포함)
  - **상태**: [x] 통과 [ ] 실패 [ ] 보류
- **TC-MCP-008: 피드 검색 도구 엔드포인트 테스트 (`test_search_feeds`)**
  - **목표**: `/api/feeds/search` GET 요청 시 쿼리 파라미터(`q`)를 사용하여 피드를 검색하고 결과를 JSON 리스트로 반환하는지 확인합니다. (결과 구조 포함)
  - **상태**: [x] 통과 [ ] 실패 [ ] 보류

## 3. RSS 피드 관련 MCP 리소스 구현 테스트

- **TC-MCP-009: MCP 리소스 등록 확인 (`test_mcp_server_resources`)**
  - **목표**: 필요한 MCP 리소스(`categories_resource`, `sources_resource`, `status_resource` 등)가 MCP 앱에 모두 등록되었는지 확인합니다.
  - **상태**: [x] 통과 [ ] 실패 [ ] 보류
- **TC-MCP-010: 피드 카테고리 리소스 엔드포인트 테스트 (`test_feeds_categories`)**
  - **목표**: `/api/feeds/categories` GET 요청 시 설정된 피드 카테고리 목록을 JSON 리스트로 반환하는지 확인합니다.
  - **상태**: [x] 통과 [ ] 실패 [ ] 보류
- **TC-MCP-011: 피드 소스 리소스 엔드포인트 테스트 (`test_feeds_sources`)**
  - **목표**: `/api/feeds/sources` GET 요청 시 설정된 피드 소스 목록을 JSON 리스트로 반환하는지 확인합니다.
  - **상태**: [x] 통과 [ ] 실패 [ ] 보류

## 4. MCP 음성 기능 구현 테스트

- **TC-MCP-012: MCP 음성 관련 도구 등록 확인 (`test_mcp_server_tools` 내)**
  - **목표**: 음성 관련 도구(`speak_summary_tool`, `read_latest_news_tool`)가 MCP 앱에 등록되었는지 확인합니다.
  - **상태**: [x] 통과 [ ] 실패 [ ] 보류 
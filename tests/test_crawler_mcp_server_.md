# 웹 크롤러 MCP 서버 개발 계획

## 태스크: 웹 크롤러 MCP 서버 구현

- [x] Playwright 기반 브라우저 풀 관리자(`BrowserPoolManager`) 구현
- [x] MCP 도구 정의 (`launch_browser`, `crawl_page`, `extract_content`, `interact_with_page`, `follow_links`)
    - [x] `launch_browser`: 브라우저 풀 상태 확인 및 초기화 (필요시)
    - [x] `crawl_page`: 주어진 URL 크롤링 및 기본 정보 반환
    - [x] `extract_content`: 주어진 URL에서 CSS 셀렉터 기반 내용 추출
    - [ ] `interact_with_page`: 페이지 상호작용 기능 구현 (클릭, 입력 등) - *Placeholder*
    - [ ] `follow_links`: 페이지 내 링크 추적 기능 구현 - *Placeholder*
- [x] `FastMCP` 인스턴스 생성 및 lifespan 설정

## 테스트: 웹 크롤러 MCP 서버

- [x] 서버 초기화 및 lifespan 테스트 (`test_server_initialization`)
- [x] `launch_browser` 도구 테스트 (`test_launch_browser_tool`)
- [x] `crawl_page` 도구 테스트
    - [x] 성공 시나리오 (`test_crawl_page_tool_success`)
    - [x] 404 에러 시나리오 (`test_crawl_page_tool_not_found`)
- [x] `extract_content` 도구 테스트
    - [x] 성공 시나리오 (`test_extract_content_tool_success`)
    - [x] 부분 실패 시나리오 (`test_extract_content_tool_partial_fail`)
    - [x] 페이지 로드 실패 시나리오 (`test_extract_content_tool_page_fail`)
- [x] Placeholder 도구 테스트 (`test_placeholder_tools`) - *Placeholder 상태 확인*
- [ ] `interact_with_page` 도구 상세 테스트 (구현 후)
- [ ] `follow_links` 도구 상세 테스트 (구현 후) 
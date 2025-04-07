# AI 및 LLM 최신 뉴스 자동 수집·요약 시스템 구현 태스크

이 문서는 AI 및 LLM 최신 뉴스 자동 수집·요약 시스템의 구현을 위한 세부 작업 태스크를 정의합니다. 각 태스크는 OpenAI Agent 기반 및 MCP 서버 아키텍처를 활용하여 구현됩니다.

## 작업 흐름

1. 태스크 구현
2. 단위 테스트 작성 및 실행
3. 빌드 확인
4. 통합 테스트 실행
5. 문서화

## 1. 개발 환경 설정

### 1.1 기본 개발 환경
- [x] Python 3.10+ 설치 및 가상환경 설정
  - [x] Anaconda 설치
  - [x] `conda create -n sns_manage python=3.10` 명령으로 가상환경 생성
  - [x] `conda activate sns_manage` 명령으로 가상환경 활성화
  - [x] 필요한 Python 패키지 설치를 위한 환경 준비
- [x] Git 저장소 초기화 및 GitHub 연동
- [x] .gitignore 및 기본 프로젝트 구조 설정
- [x] requirements.txt 또는 Poetry 구성 파일 작성

### 1.2 의존성 설치
- [x] 기본 패키지 설치 (feedparser, requests, BeautifulSoup, aiohttp 등)
- [x] OpenAI API 패키지 설치
- [x] FastAPI, Uvicorn 설치
- [x] 테스트 도구 설치 (pytest, pytest-asyncio)
- [x] MCP Python SDK 설치

### 1.3 API 키 및 설정 구성
- [x] OpenAI API 키 발급 및 설정
- [x] 네이버 개발자 센터 앱 등록 및 API 키 발급
- [x] 설정 파일 구조 생성 (config.py 또는 .env)
- [x] 보안 관련 설정 (API 키 보호 등)

### 1.4 프로젝트 구조 완성
- [x] 모듈별 디렉토리 구조 설정
- [x] MCP 서버 템플릿 디렉토리 구성
- [x] 테스트 디렉토리 구조 설정
- [x] 기본 로깅 시스템 구현

## 2. 데이터 수집 모듈 구현

### 2.1 RSS 피드 수집 모듈
- [x] RSS 피드 소스 리스트 정의 및 우선순위 설정
  - [x] **주요 AI 연구/기업 블로그**: OpenAI Blog, Google AI Blog, Meta AI Blog, Microsoft Research
  - [x] **AI 전문 미디어**: VentureBeat AI, MIT Technology Review AI, The AI Journal, AI Trends
  - [x] **일반 기술 미디어의 AI 섹션**: TechCrunch AI, Wired AI, The Verge AI, CNET AI
  - [x] **학술 정보 피드**: arXiv CS.AI, ACM AI Magazine, IEEE Spectrum AI
  - [x] **한국 AI 관련 피드**: 네이버 AI 뉴스, AI 타임스, 전자신문 AI 섹션
  - [x] **구독형 뉴스레터 아카이브**: AI Weekly, Import AI, ML Research Roundup
- [x] 각 피드별 RSS URL 수집 및 검증
- [x] 피드 카테고리 분류 체계 구축 (연구, 제품, 산업, 정책 등)
- [x] feedparser 기반 RSS 수집 기능 구현
- [x] 피드 데이터 정규화 및 메타데이터 추출 로직 구현
  - [x] 제목, 요약, 본문, 발행일, 저자, 카테고리, 태그 등 표준화
  - [x] AI/LLM 관련성 초기 판단 로직 구현
- [x] 피드 갱신 주기 최적화 (사이트별 업데이트 빈도 반영)
- [x] 오류 처리 및 재시도 메커니즘 구현
- [x] 수집 결과 임시 저장 기능 구현 (JSON 형식)

### 2.2 RSS-MCP 서버 구현
- [x] MCP 서버 기본 구조 설계
  - [x] MCP FastMCP 클래스 기반 앱 구현
  - [x] 서버 설정 및 초기화 코드 구현
  - [x] 에러 처리 및 로깅 기능 구현
- [x] RSS 피드 관련 MCP 도구 구현
  - [x] 피드 수집 도구 (collect_rss_feeds)
  - [x] 최신 피드 조회 도구 (get_latest_feeds)
  - [x] 피드 검색 도구 (search_feeds)
- [x] RSS 피드 관련 MCP 리소스 구현
  - [x] 카테고리 목록 리소스 (categories)
  - [x] 소스 목록 리소스 (sources)
  - [x] 서버 상태 리소스 (status)
  - [x] 요약 목록 리소스 (summaries)
- [x] MCP 음성 기능 구현
  - [x] 요약 읽기 도구 (speak_summary)
  - [x] 최신 뉴스 읽기 도구 (read_latest_news)
- [x] MCP-FastAPI 통합
  - [x] 별도 스레드에서 MCP 서버 실행 구현
  - [x] API 공유 및 상호 작용 구현
  - [x] 웹 UI에 MCP 상태 표시 기능 구현
- [x] RSS-MCP 서버 테스트
  - [x] 단위 테스트 작성 및 실행
  - [x] 통합 테스트 작성 및 실행
  - [x] 수동 테스트 지침서 작성

### 2.3 웹 크롤링 MCP 서버 구현
- [x] MCP 서버 구조 설정
- [x] Playwright 기반 크롤링 도구 함수 정의
  - [x] `launch_browser()` - 브라우저 인스턴스 초기화 및 구성
  - [x] `crawl_page(url)` - 지정된 URL의 전체 페이지 크롤링
  - [x] `extract_content(page, selectors)` - 특정 선택자 기반 콘텐츠 추출
  - [ ] `interact_with_page(page, actions)` - 페이지 상호작용 수행
  - [ ] `follow_links(page, pattern)` - 특정 패턴의 링크 추적
- [x] 브라우저 풀 관리 기능 구현
  - [x] 브라우저 인스턴스 재사용 및 리소스 최적화
  - [ ] 병렬 페이지 크롤링 관리
- [x] 오류 처리 및 로깅
  - [ ] 브라우저 충돌 복구 메커니즘
  - [ ] 네트워크 오류 감지 및 재시도 로직
  - [ ] 성능 및 리소스 사용량 모니터링

### 2.4 데이터 수집 관리 및 에이전트 구현
- [x] 데이터 수집 작업 스케줄러 구현
  - [x] 사이트별 최적 크롤링 시간 설정
  - [x] 우선순위 기반 수집 작업 관리
  - [x] 관련 단위 테스트 작성 및 통과 (`tests/scheduler/test_scheduler.py`)
- [x] 수집 데이터 중앙 저장소 구현
  - [x] RSS와 크롤링 데이터 통합 저장 스키마 설계
  - [x] 중복 데이터 처리 메커니즘
  - [x] SQLite 기반 저장소 구현 및 테스트 (`app/repository/sqlite_store.py`, `tests/repository/test_sqlite_store.py`)
- [x] 모니터링 기능 구현
  - [x] 모니터링 로그 DB 모델 및 Enum 정의
  - [x] `SQLiteMonitoringRepository` 구현
  - [x] 태스크 로깅 통합
- [x] 수집 API 구현 (다른 모듈에서 수집 데이터 요청용)
- [x] OpenAI Agent 설정 (Collector Agent)
  - [x] 에이전트 프롬프트 템플릿 설계 및 최적화
  - [x] 명확한 역할 및 목표 정의
  - [x] 에이전트 도구 구현
    - [x] 데이터 관리 도구 (`get_collected_data_tool`, `save_collected_data_tool`)
    - [x] 데이터 수집 도구 (`collect_rss_feeds_tool`, `crawl_webpage_tool`)
    - [x] 스케줄러 도구 (`schedule_collection_task_tool`, `check_task_status_tool`, `list_scheduled_tasks_tool`)
    - [x] 모니터링 도구 (`log_monitoring_start_tool`, `log_monitoring_end_tool`)
    - [x] 평가 도구 (`evaluate_source_quality_tool`)
    - [x] 에이전트 도구 단위 테스트 구현 및 통과 (`tests/agents/tools/*.py`)
- [ ] RSS-MCP 및 크롤링-MCP 서버 연동
  - [ ] API 및 인터페이스 연동
  - [ ] 도구 호출 오케스트레이션
- [ ] 지능형 데이터 소스 평가 및 선택 로직 구현
  - [ ] 콘텐츠 품질 및 관련성 기반 소스 평가
  - [ ] 동적 소스 우선순위 조정
- [ ] 새로운 데이터 소스 발견 기능 (선택적)
  - [ ] 기존 콘텐츠에서 새로운 소스 링크 추출
  - [ ] 소스 품질 평가 및 추가 프로세스
- [ ] 수집 작업 스케줄링 및 모니터링 기능 통합 관리 (Agent가 스케줄러/모니터링 시스템 사용)

## 3. 콘텐츠 선별 모듈 구현

### 3.1 기본 키워드 필터링
- [ ] AI/LLM 관련 핵심 키워드 리스트 정의
- [ ] 제목 및 본문 키워드 매칭 로직 구현
- [ ] 가중치 기반 관련성 점수 계산 알고리즘
- [ ] 임계값 기반 필터링 구현
- [ ] 필터링 결과 저장 기능 구현

### 3.2 중복 콘텐츠 감지
- [ ] URL 기반 기본 중복 감지 구현
- [ ] 제목 유사도 계산 로직 구현
- [ ] 임베딩 기반 콘텐츠 유사도 계산 (기본 구현)
- [ ] 중복 뉴스 그룹화 기능 구현
- [ ] 중복 판정 이력 저장 기능

### 3.3 콘텐츠 선별 MCP 서버 구현
- [ ] MCP 서버 구조 설정
- [ ] 필터링 도구 함수 정의 (`filter_by_keywords()`, `detect_duplicates()`, `rank_relevance()`)
- [ ] 가중치 및 설정 조정 인터페이스 구현
- [ ] 필터링 결과 포맷 정의
- [ ] 필터링 로직 설명 기능 구현

### 3.4 선별 에이전트 구현
- [ ] OpenAI Agent 설정 (Curator Agent)
- [ ] 콘텐츠 선별 MCP 서버 연동
- [ ] 에이전트 프롬프트 및 판단 기준 정의
- [ ] 트렌드 감지 및 주제 그룹화 로직 구현
- [ ] 사용자 피드백 학습 메커니즘 (기본 구현)

## 4. 콘텐츠 요약 및 분석 모듈 구현

### 4.1 LLM 기반 요약 기능
- [ ] OpenAI GPT API 또는 GEMMA3 API 연동
- [ ] 요약용 프롬프트 템플릿 설계
- [ ] 뉴스 본문 전처리 로직 구현
- [ ] 토큰 제한 관리 기능 구현
- [ ] 요약 결과 후처리 및 포맷팅

### 4.2 분석 및 맥락화 기능
- [ ] 기사 분석용 프롬프트 템플릿 설계
- [ ] 산업 영향 및 의미 추출 로직 구현
- [ ] 관련 주제 및 배경 정보 연결 기능
- [ ] 해시태그 생성 알고리즘 구현
- [ ] 분석 결과 정규화 및 저장

### 4.3 요약 생성 MCP 서버 구현
- [ ] MCP 서버 구조 설정
- [ ] 요약 도구 함수 정의 (`summarize_article()`, `analyze_impact()`, `generate_tags()`)
- [ ] LLM API 호출 최적화 및 캐싱
- [ ] 오류 처리 및 폴백 전략 구현
- [ ] 요약 품질 자가 평가 기능 구현

### 4.4 요약 에이전트 구현
- [ ] OpenAI Agent 설정 (Summarizer Agent)
- [ ] 요약 생성 MCP 서버 연동
- [ ] 에이전트 프롬프트 및 행동 정의
- [ ] 아티클 특성에 따른 요약 전략 조정 기능
- [ ] 요약 내용 확인 및 교정 로직 구현

## 5. 콘텐츠 편집 및 검토 모듈 구현

### 5.1 편집 인터페이스 기본 구현
- [ ] 웹 기반 편집 인터페이스 설계
- [ ] 요약 편집 기능 구현
- [ ] 분석 내용 편집 기능 구현
- [ ] 게시 전 최종 검토 기능
- [ ] 사용자 권한 관리

### 5.2 편집 에이전트 구현 (선택적)
- [ ] OpenAI Agent 설정 (Editor Agent)
- [ ] 편집 및 교정 자동화 지원
- [ ] 스타일 가이드 적용 및 일관성 유지
- [ ] 콘텐츠 개선 제안 기능

## 6. 콘텐츠 게시 모듈 구현

### 6.1 게시 플랫폼 연동
- [ ] 네이버 카페 API 연동 구현
  - [ ] OAuth 인증 처리
  - [ ] 게시글 작성 및 등록 기능 구현
  - [ ] 이미지 및 첨부파일 처리
- [ ] 기타 플랫폼 연동 (선택적: 블로그, SNS 등)

### 6.2 게시 스케줄링 및 관리
- [ ] 게시 시간 최적화 로직 구현
- [ ] 예약 게시 기능 구현
- [ ] 게시 결과 모니터링 및 로깅
- [ ] 게시 실패 시 재시도 메커니즘

### 6.3 게시 에이전트 구현
- [ ] OpenAI Agent 설정 (Publisher Agent)
- [ ] 게시 플랫폼 연동 모듈 제어
- [ ] 게시 콘텐츠 최종 검토 및 형식 지정
- [ ] 사용자 상호작용 처리 (댓글 등)

## 7. 시스템 통합 및 배포

### 7.1 모듈 통합
- [ ] 각 모듈 API 통합 테스트
- [ ] 전체 시스템 워크플로우 테스트
- [ ] 성능 및 부하 테스트

### 7.2 사용자 인터페이스 개발
- [ ] FastAPI 기반 웹 UI 구현
  - [ ] 대시보드: 시스템 상태 및 통계 시각화
  - [ ] 콘텐츠 목록 및 상세 조회 화면
  - [ ] 편집 및 검토 인터페이스 연동
  - [ ] 설정 관리 화면

### 7.3 배포
- [ ] Dockerfile 작성 및 컨테이너화
- [ ] 클라우드 플랫폼 배포 (AWS, GCP, Azure 등)
- [ ] CI/CD 파이프라인 구축
- [ ] 운영 환경 설정 및 모니터링

## 8. 문서화 및 유지보수

### 8.1 기술 문서화
- [ ] 시스템 아키텍처 문서
- [ ] API 명세서
- [ ] 모듈별 구현 상세 문서
- [ ] 배포 및 운영 가이드

### 8.2 사용자 매뉴얼
- [ ] 시스템 사용 방법 안내
- [ ] 문제 해결 가이드

### 8.3 유지보수 계획
- [ ] 정기 업데이트 및 패치 계획
- [ ] 버그 추적 및 관리 시스템
- [ ] 사용자 지원 채널

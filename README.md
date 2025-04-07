# AI 및 LLM 최신 뉴스 자동 수집·요약 시스템

AI 및 LLM 관련 최신 뉴스를 자동으로 수집하고 요약하여 네이버 카페 등에 게시하는 시스템입니다.

## 시스템 개요

이 시스템은 다음 모듈로 구성됩니다:

- **수집 모듈**: RSS 피드, 웹 크롤링을 통한 AI 관련 뉴스 자동 수집
- **선별 모듈**: 키워드 필터링, 출처 신뢰도, 트렌드 등을 기준으로 콘텐츠 선별
- **생성 모듈**: LLM 기반 요약 및 분석 자동 생성
- **게시 모듈**: 사용자 검토/수정 후 네이버 카페 등에 선택적 게시

## 설치 방법

### 환경 설정

```bash
# Anaconda 환경 생성 및 활성화
conda create -n sns_manage python=3.10
conda activate sns_manage

# 의존성 설치
pip install -r requirements.txt
```

## 사용 방법

```bash
# 개발 서버 실행
uvicorn app.main:app --reload
```

## 개발 가이드

프로젝트 구조:
```
ai-news-system/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI 애플리케이션 진입점
│   ├── config.py          # 설정 관리
│   ├── collector/         # 데이터 수집 모듈
│   ├── processor/         # 데이터 처리 및 필터링 모듈
│   ├── summarizer/        # LLM 기반 요약 모듈
│   ├── publisher/         # 게시 모듈
│   ├── models/            # 데이터 모델
│   ├── api/               # API 라우트
│   ├── scheduler/         # 작업 스케줄러
│   └── templates/         # 웹 UI 템플릿
├── static/                # 정적 파일 (CSS, JS)
├── data/                  # 임시 데이터 저장소
├── tests/                 # 테스트 코드
├── requirements.txt       # 의존성 목록
└── README.md              # 프로젝트 문서
```

## 라이센스

MIT

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union

from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 프로젝트 루트 경로
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR

# 개발 환경 설정
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
ENV = os.getenv("ENV", "development")

# API 키 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")

# 데이터 경로 설정
DATA_DIR = BASE_DIR / "data"
os.makedirs(DATA_DIR, exist_ok=True)

# 정적 파일 및 템플릿 경로
STATIC_DIR = BASE_DIR / "static"
os.makedirs(STATIC_DIR, exist_ok=True)
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# 임시 데이터 디렉토리
RAW_FEEDS_DIR = DATA_DIR / "raw_feeds"
os.makedirs(RAW_FEEDS_DIR, exist_ok=True)
FILTERED_FEEDS_DIR = DATA_DIR / "filtered_feeds"
os.makedirs(FILTERED_FEEDS_DIR, exist_ok=True)
SUMMARIES_DIR = DATA_DIR / "summaries"
os.makedirs(SUMMARIES_DIR, exist_ok=True)

# 서버 설정
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
API_PREFIX = "/api"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# MCP 서버 설정
MCP_ENABLED = os.getenv("MCP_ENABLED", "True").lower() == "true"
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_PORT", "8100"))

# RSS 피드 설정
RSS_SOURCES = [
    # 주요 AI 연구/기업 블로그
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml", "category": "research"},
    {"name": "Google AI Blog", "url": "http://googleaiblog.blogspot.com/atom.xml", "category": "research"},
    {"name": "Meta AI Blog", "url": "https://ai.meta.com/blog/rss/", "category": "research"},
    {"name": "Microsoft Research", "url": "https://www.microsoft.com/en-us/research/feed/", "category": "research"},
    
    # AI 전문 미디어
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/", "category": "media"},
    {"name": "MIT Technology Review AI", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed", "category": "media"},
    {"name": "AI Trends", "url": "https://aitrends.com/feed/", "category": "media"},
    
    # 일반 기술 미디어의 AI 섹션
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/", "category": "tech"},
    {"name": "Wired AI", "url": "https://www.wired.com/tag/artificial-intelligence/feed/", "category": "tech"},
    {"name": "The Verge AI", "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml", "category": "tech"},
    
    # 학술 정보 피드
    {"name": "arXiv CS.AI", "url": "http://export.arxiv.org/rss/cs.AI", "category": "academic"},
    
    # 한국 AI 관련 피드
    {"name": "AI 타임스", "url": "https://www.aitimes.com/rss/allArticle.xml", "category": "korea"},
]

# 키워드 필터링 설정
KEYWORDS = {
    "must_include": [
        "AI", "인공지능", "artificial intelligence", "machine learning", "머신러닝",
        "LLM", "GPT", "대형 언어 모델", "large language model", "deep learning", "딥러닝"
    ],
    "additional_weight": [
        "OpenAI", "Anthropic", "Claude", "Gemini", "Gemma", "Mistral", "LLaMa", "GPT-4", "GPT-5",
        "multimodal", "멀티모달", "강화학습", "reinforcement learning", "diffusion", "디퓨전",
        "transformer", "트랜스포머", "attention", "어텐션", "fine-tuning", "파인튜닝"
    ],
    "exclude": [
        "sponsored", "광고", "advertisement"
    ]
}

# 요약 설정
SUMMARY_CONFIG = {
    "max_tokens": 500,
    "temperature": 0.3,
    "model": "gpt-4-turbo",
    "summary_length": "medium",  # short, medium, long
}

# 게시 설정
PUBLISH_CONFIG = {
    "naver_cafe_id": os.getenv("NAVER_CAFE_ID", ""),
    "naver_cafe_menu_id": os.getenv("NAVER_CAFE_MENU_ID", ""),
    "post_interval_minutes": 30,  # 게시 간격 (분)
    "max_posts_per_day": 10,  # 하루 최대 게시 수
}

# 로깅 설정
LOG_LEVEL = "DEBUG" if DEBUG else "INFO"
LOG_DIR = BASE_DIR / "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 스케줄러 설정
SCHEDULER_CONFIG = {
    "collect_interval_minutes": 60,  # 수집 간격 (분)
    "filter_interval_minutes": 120,  # 필터링 간격 (분)
    "summarize_interval_minutes": 180,  # 요약 간격 (분)
    "publish_interval_minutes": 240,  # 게시 간격 (분)
}

# API 버전 및 정보
API_VERSION = "1.0.0"
API_TITLE = "AI 뉴스 자동 수집·요약 시스템 API"
API_DESCRIPTION = "AI 및 LLM 관련 최신 뉴스를 자동으로 수집하고 요약하는 서비스 API"
API_CONTACT = {
    "name": "AI News Manager",
    "email": "ai.news.manager@example.com",
}

SUMMARY_MAX_TOKENS = 500
SUMMARY_TEMPERATURE = 0.7

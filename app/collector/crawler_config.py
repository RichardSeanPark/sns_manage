"""크롤링 대상 사이트 설정"""

CRAWLER_CONFIG = {
    # AI 연구 기관 웹사이트
    "openai": {
        "name": "OpenAI",
        "base_url": "https://openai.com",
        "paths": [
            "/research",
            "/blog"
        ],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": "article",
        "update_interval": 24,  # 시간 단위
        "priority": 1
    },
    "anthropic": {
        "name": "Anthropic",
        "base_url": "https://www.anthropic.com",
        "paths": [
            "/research"
        ],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": "article",
        "update_interval": 24,
        "priority": 1
    },
    "deepmind": {
        "name": "Google DeepMind",
        "base_url": "https://deepmind.google",
        "paths": [
            "/research"
        ],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": "article",
        "update_interval": 24,
        "priority": 1
    },
    "meta_ai": {
        "name": "Meta AI",
        "base_url": "https://ai.meta.com",
        "paths": [
            "/research"
        ],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": "article",
        "update_interval": 24,
        "priority": 1
    },
    "microsoft_research": {
        "name": "Microsoft Research AI",
        "base_url": "https://www.microsoft.com",
        "paths": [
            "/en-us/research/research-area/artificial-intelligence"
        ],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": "article",
        "update_interval": 24,
        "priority": 1
    },

    # AI 전문 뉴스 사이트
    "ai_news": {
        "name": "AI News",
        "base_url": "https://artificialintelligence-news.com",
        "paths": [
            "/news",
            "/articles"
        ],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": ".entry-content",
        "update_interval": 6,
        "priority": 2
    },
    "aitopics": {
        "name": "AITopics",
        "base_url": "https://aitopics.org",
        "paths": [
            "/news"
        ],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": ".content",
        "update_interval": 12,
        "priority": 2
    },
    "analytics_insight": {
        "name": "Analytics Insight AI",
        "base_url": "https://www.analyticsinsight.net",
        "paths": [
            "/category/artificial-intelligence"
        ],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": ".entry-content",
        "update_interval": 6,
        "priority": 2
    },

    # 한국 AI 관련 사이트
    "ai_times": {
        "name": "AI 타임스",
        "base_url": "https://www.aitimes.com",
        "paths": [
            "/"
        ],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": ".article-body",
        "update_interval": 4,
        "priority": 1
    },
    "etnews_ai": {
        "name": "전자신문 AI 섹션",
        "base_url": "https://www.etnews.com",
        "paths": [
            "/news/section.html?id1=02&id2=06"
        ],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": ".article_body",
        "update_interval": 4,
        "priority": 1
    },
    "naver_ai": {
        "name": "네이버 AI 랩",
        "base_url": "https://clova.ai",
        "paths": [
            "/ko/research/research-areas.html"
        ],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": ".content",
        "update_interval": 24,
        "priority": 2
    },
    "kakao_ai": {
        "name": "카카오 AI",
        "base_url": "https://tech.kakao.com",
        "paths": [
            "/tag/ai"
        ],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": ".post-content",
        "update_interval": 24,
        "priority": 2
    },

    # AI 제품 런칭 사이트
    "product_hunt_ai": {
        "name": "Product Hunt AI",
        "base_url": "https://www.producthunt.com",
        "paths": [
            "/topics/artificial-intelligence"
        ],
        "article_selector": ".post-item",
        "title_selector": "h3",
        "content_selector": ".post-tagline",
        "update_interval": 12,
        "priority": 3
    },
    "huggingface": {
        "name": "HuggingFace",
        "base_url": "https://huggingface.co",
        "paths": [
            "/blog"
        ],
        "article_selector": "article",
        "title_selector": "h1",
        "content_selector": ".prose",
        "update_interval": 24,
        "priority": 2
    }
}

# 크롤링 전략 설정
CRAWLING_STRATEGY = {
    "max_retries": 3,  # 최대 재시도 횟수
    "retry_delay": 5,  # 재시도 대기 시간 (초)
    "concurrent_limit": 5,  # 동시 크롤링 제한
    "request_delay": 2,  # 요청 간 대기 시간 (초)
    "timeout": 30,  # 요청 타임아웃 (초)
    "headers": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
}

# 크롤링 결과 저장 설정
STORAGE_CONFIG = {
    "base_dir": "data/crawled",  # 크롤링 결과 저장 기본 디렉토리
    "format": "json",  # 저장 형식
    "backup_enabled": True,  # 백업 활성화
    "backup_interval": 24,  # 백업 주기 (시간)
    "compression_enabled": True  # 압축 활성화
} 
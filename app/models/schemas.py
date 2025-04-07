from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class FeedSource(BaseModel):
    """RSS 피드 소스 정보 스키마"""
    name: str
    url: HttpUrl
    category: str


class FeedItem(BaseModel):
    """RSS 피드 아이템 스키마"""
    id: str
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    link: HttpUrl
    published: datetime
    updated: Optional[datetime] = None
    source_name: str
    source_url: HttpUrl
    source_category: str
    tags: List[str] = Field(default_factory=list)
    relevance_score: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class FilteredItem(FeedItem):
    """필터링된 피드 아이템 스키마"""
    is_relevant: bool = False
    relevance_score: float = 0.0
    matched_keywords: List[str] = Field(default_factory=list)
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None


class Summary(BaseModel):
    """뉴스 요약 스키마"""
    feed_item_id: str
    title: str
    summary_text: str
    analysis_text: Optional[str] = None
    hashtags: List[str] = Field(default_factory=list)
    source_link: HttpUrl
    source_name: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }


class PublishItem(BaseModel):
    """게시 아이템 스키마"""
    summary_id: str
    title: str
    content: str
    hashtags: List[str] = Field(default_factory=list)
    source_link: HttpUrl
    source_name: str
    status: str = "draft"  # draft, pending, published, failed
    platform: str = "naver_cafe"
    published_at: Optional[datetime] = None
    platform_post_id: Optional[str] = None
    platform_post_url: Optional[HttpUrl] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

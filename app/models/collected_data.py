import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl, validator

from .enums import SourceType, ProcessingStatus # Enum 임포트

class CollectedData(BaseModel):
    """수집된 뉴스 데이터(RSS, 웹 크롤링 등)를 위한 통합 모델"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="고유 식별자")
    source_url: HttpUrl = Field(..., description="데이터 출처 URL")
    source_type: SourceType = Field(..., description="데이터 소스 유형")
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="데이터 수집 시각 (UTC)")

    title: Optional[str] = Field(None, description="기사 또는 페이지 제목")
    link: Optional[HttpUrl] = Field(None, description="원본 콘텐츠 링크")
    published_at: Optional[datetime] = Field(None, description="콘텐츠 발행 시각 (UTC, 가능한 경우)")
    summary: Optional[str] = Field(None, description="콘텐츠 요약 또는 설명")
    content: Optional[str] = Field(None, description="추출된 주요 텍스트 본문")
    author: Optional[str] = Field(None, description="저자 정보")
    categories: List[str] = Field(default_factory=list, description="카테고리 목록")
    tags: List[str] = Field(default_factory=list, description="태그 목록")

    relevance_score: Optional[float] = Field(None, description="AI/LLM 관련성 점수 (선택적)")
    processing_status: ProcessingStatus = Field(ProcessingStatus.RAW, description="처리 상태")

    # 추가 메타데이터 (소스별 특화 정보 등 저장용)
    extra_data: Dict[str, Any] = Field(default_factory=dict, description="추가 메타데이터")

    class Config:
        # MongoDB 등 NoSQL DB 사용 시 _id 필드 허용
        # allow_population_by_field_name = True
        # orm_mode = True # SQLAlchemy 등 ORM 사용 시
        use_enum_values = True # Enum 값을 사용하도록 설정
        json_encoders = {
            datetime: lambda dt: dt.isoformat(),
            HttpUrl: lambda url: str(url)
        }

    @validator('published_at', pre=True, always=True)
    def ensure_published_at_utc(cls, v):
        """published_at 필드를 UTC로 변환 (timezone 정보가 없는 경우 UTC로 가정)"""
        if isinstance(v, datetime):
            if v.tzinfo is None:
                return v.replace(tzinfo=timezone.utc)
            return v.astimezone(timezone.utc)
        # TODO: 문자열 등 다른 타입의 날짜 변환 로직 추가 필요 (예: dateutil.parser 사용)
        return v

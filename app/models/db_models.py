from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, JSON, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from datetime import datetime
import os

# 데이터베이스 경로 (config에서 가져오도록 변경 예정)
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# SQLALCHEMY_DATABASE_URL = "sqlite:///" + os.path.join(BASE_DIR, "./collected_news.db")

# engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class CollectedDataDB(Base):
    __tablename__ = "collected_data"

    id: str = Column(String, primary_key=True, index=True)
    source_url: str = Column(String, nullable=False)
    source_type: str = Column(String, index=True, nullable=False)
    collected_at: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    title: str = Column(String, index=True, nullable=True) # 제목은 null 가능, 검색 위해 인덱스 추가
    link: str = Column(String, nullable=True)
    published_at: datetime = Column(DateTime(timezone=True), nullable=True)
    summary: str = Column(Text, nullable=True)
    content: str = Column(Text, nullable=True)
    author: str = Column(String, nullable=True)
    categories = Column(JSON, nullable=True)  # 리스트를 JSON 문자열로 저장
    tags = Column(JSON, nullable=True)        # 리스트를 JSON 문자열로 저장

    relevance_score: float = Column(Float, nullable=True)
    processing_status: str = Column(String, default='raw')

    extra_data = Column(JSON, nullable=True)    # 필드 이름 변경

    # 검색 효율성을 위한 인덱스 추가 (선택적)
    __table_args__ = (
        Index('ix_collected_data_source_url', 'source_url'),
        Index('ix_collected_data_published_at', 'published_at'),
        Index('ix_collected_data_status', 'processing_status'),
    )

# 데이터베이스 및 테이블 생성 함수 (필요시 사용)
# def create_db_and_tables(engine_to_use):
#     Base.metadata.create_all(bind=engine_to_use)

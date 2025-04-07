from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, JSON, Index, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func
from datetime import datetime
import os
from .enums import MonitoringStatus

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

# --- 모니터링 로그 모델 ---
class MonitoringLogDB(Base):
    __tablename__ = "monitoring_log"

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    task_name: str = Column(String, nullable=False)
    start_time: datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end_time: datetime = Column(DateTime(timezone=True), nullable=True) # 작업 종료 시 업데이트
    status: str = Column(String, nullable=False) # MonitoringStatus 값 저장
    items_processed: int = Column(Integer, nullable=True)
    items_succeeded: int = Column(Integer, nullable=True)
    items_failed: int = Column(Integer, nullable=True)
    error_message: str = Column(Text, nullable=True) # 실패 시 상세 오류 메시지
    details: dict = Column(JSON, nullable=True) # 추가 정보 (e.g., 실패한 URL 리스트)

    # 검색 편의를 위한 인덱스 추가
    __table_args__ = (
        Index('ix_monitoring_log_task_name', 'task_name'),
        Index('ix_monitoring_log_status', 'status'),
        Index('ix_monitoring_log_start_time', 'start_time'),
    )

# 데이터베이스 및 테이블 생성 함수 (필요시 사용)
# def create_db_and_tables(engine_to_use):
#     Base.metadata.create_all(bind=engine_to_use)

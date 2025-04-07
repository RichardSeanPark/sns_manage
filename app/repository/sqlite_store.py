import logging
from typing import List, Optional, Any, Dict, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, select, update, delete, func, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.models.collected_data import CollectedData
from app.models.db_models import CollectedDataDB, Base
from app.repository.base import BaseRepository
from app.utils.data_processing import is_title_duplicate
from app.config import DATABASE_URL, DB_CONNECT_ARGS
from app.models.enums import SourceType, ProcessingStatus

logger = logging.getLogger(__name__)

class SQLiteRepository(BaseRepository):
    """SQLite 데이터베이스를 사용하는 저장소 구현"""

    def __init__(self, db_url: str = DATABASE_URL, connect_args: dict = None):
        if connect_args is None:
            connect_args = DB_CONNECT_ARGS
        try:
            self.engine = create_engine(db_url, connect_args=connect_args)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            self._create_tables()
            logger.info(f"SQLiteRepository initialized with db: {db_url}")
        except SQLAlchemyError as e:
            logger.error(f"Failed to initialize SQLiteRepository: {e}", exc_info=True)
            raise

    def _create_tables(self):
        """데이터베이스에 테이블이 없으면 생성합니다."""
        try:
            # 테이블 존재 여부 확인 (더 안정적인 방법)
            inspector = inspect(self.engine)
            if not inspector.has_table(CollectedDataDB.__tablename__):
                 Base.metadata.create_all(bind=self.engine)
                 logger.info(f"Table '{CollectedDataDB.__tablename__}' created.")
            else:
                 logger.info(f"Table '{CollectedDataDB.__tablename__}' already exists.")
        except SQLAlchemyError as e:
            logger.error(f"Failed to create tables: {e}", exc_info=True)
            # 필요한 경우 여기서 에러를 다시 raise 할 수 있습니다.


    @contextmanager
    def get_db(self) -> Generator[Session, None, None]:
        """데이터베이스 세션 컨텍스트 관리자"""
        db: Session = self.SessionLocal()
        try:
            yield db
        except SQLAlchemyError as e:
            logger.error(f"Database session error: {e}", exc_info=True)
            db.rollback()
            raise # 또는 적절한 예외 처리
        finally:
            db.close()

    def _map_pydantic_to_db(self, data: CollectedData) -> CollectedDataDB:
        """Pydantic 모델을 SQLAlchemy 모델로 변환 (단순 매핑)"""
        db_data = CollectedDataDB(
            id=data.id,
            source_url=str(data.source_url), # HttpUrl -> str
            source_type=data.source_type, # 이미 str 값 (use_enum_values=True)
            collected_at=data.collected_at,
            title=data.title,
            link=str(data.link) if data.link else None, # HttpUrl -> str
            published_at=data.published_at,
            summary=data.summary,
            content=data.content,
            author=data.author,
            categories=data.categories, # JSON으로 저장
            tags=data.tags,             # JSON으로 저장
            relevance_score=data.relevance_score,
            processing_status=data.processing_status, # 이미 str 값 (use_enum_values=True)
            extra_data=data.extra_data
        )
        return db_data

    def _map_db_to_pydantic(self, db_data: CollectedDataDB) -> CollectedData:
        """SQLAlchemy 모델을 Pydantic 모델로 변환"""
        # Pydantic 모델의 필드만 사용하여 validate
        model_data = db_data.__dict__.copy()
        # SQLAlchemy 내부 상태(_sa_instance_state) 제거
        model_data.pop('_sa_instance_state', None)
        # source_type과 processing_status를 Enum으로 변환 시도
        try:
            model_data['source_type'] = SourceType(model_data.get('source_type'))
        except (ValueError, TypeError):
            model_data['source_type'] = SourceType.UNKNOWN # 변환 실패 시 기본값
        try:
            model_data['processing_status'] = ProcessingStatus(model_data.get('processing_status'))
        except (ValueError, TypeError):
            model_data['processing_status'] = ProcessingStatus.ERROR # 변환 실패 시 에러 상태
            
        return CollectedData.model_validate(model_data)


    async def save_data(self, data: CollectedData, check_duplicates: bool = True, similarity_threshold: float = 0.8) -> Optional[CollectedData]:
        """단일 데이터 항목을 저장합니다. 제목 기반 중복 체크 포함.
        ID 중복 (IntegrityError) 발생 시 None을 반환합니다.
        """
        if not data.title:
            logger.warning(f"Data with ID {data.id} has no title, saving without duplicate check.")
            check_duplicates = False

        if check_duplicates:
            try:
                is_duplicate = await self.check_title_exists(data.title, threshold=similarity_threshold)
                if is_duplicate:
                    logger.info(f"Duplicate title found for '{data.title}' (Similarity >= {similarity_threshold}). Skipping save.")
                    return None
            except Exception as e:
                 logger.error(f"Error checking title duplication for '{data.title}': {e}", exc_info=True)
                 pass

        db_data_to_save = self._map_pydantic_to_db(data)
        
        try:
            with self.get_db() as db:
                # 바로 삽입 시도
                db.add(db_data_to_save)
                db.commit()
                db.refresh(db_data_to_save)
                logger.debug(f"Saved data with ID: {db_data_to_save.id}, Title: {db_data_to_save.title}")
                return self._map_db_to_pydantic(db_data_to_save)

        except IntegrityError as e: 
            # IntegrityError 발생 시 ID 중복으로 간주하고 None 반환
            # 롤백은 컨텍스트 매니저가 처리
            logger.warning(f"IntegrityError saving ID {data.id}, likely duplicate. Returning None.")
            return None # 데이터를 다시 조회하지 않음

        except SQLAlchemyError as e: # 다른 DB 오류
            logger.error(f"SQLAlchemyError saving data with ID {data.id}: {e}", exc_info=True)
            return None

        except Exception as e: # 그 외 예외
            logger.error(f"Unexpected error saving data {data.id}: {e}", exc_info=True)
            return None


    async def save_bulk_data(self, data_list: List[CollectedData]) -> List[CollectedData]:
        """여러 데이터 항목을 한 번에 저장합니다. (중복 체크 없음)"""
        saved_items = []
        db_items = []
        ids_to_save = set()
        for data in data_list:
             # 간단한 ID 중복 방지
             if data.id not in ids_to_save:
                 db_items.append(self._map_pydantic_to_db(data))
                 ids_to_save.add(data.id)

        if not db_items:
             return []

        try:
             with self.get_db() as db:
                 # TODO: 벌크 저장 시 DB 레벨에서 ID 충돌 처리 확인 필요 (DB 종류에 따라 다름)
                 # SQLite의 경우 INSERT OR IGNORE 등을 고려할 수 있으나, ORM에서는 복잡할 수 있음.
                 # 우선은 add_all 후 commit 시 예외 발생 가능성 있음.
                 db.add_all(db_items)
                 db.commit()
                 # 벌크 저장 후 refresh는 어려우므로, 입력 데이터를 기반으로 반환
                 # DB 기본값(collected_at 등)은 반영되지 않을 수 있음
                 saved_items = [d for d in data_list if d.id in ids_to_save]
                 logger.info(f"Attempted to save {len(db_items)} items in bulk. Result count: {len(saved_items)}")
                 return saved_items
        except SQLAlchemyError as e:
             logger.error(f"Failed to save bulk data: {e}", exc_info=True)
             # 부분 성공 시 처리 등 복잡한 로직 추가 가능
             return [] # 실패 시 빈 리스트 반환

    async def get_data_by_id(self, data_id: str) -> Optional[CollectedData]:
        """ID를 기준으로 단일 데이터 항목을 조회합니다."""
        try:
            with self.get_db() as db:
                db_data = db.get(CollectedDataDB, data_id)
                if db_data:
                    return self._map_db_to_pydantic(db_data)
                return None
        except SQLAlchemyError as e:
            logger.error(f"Failed to get data by ID {data_id}: {e}", exc_info=True)
            return None

    async def get_all_data(self, limit: int = 100, skip: int = 0) -> List[CollectedData]:
        """모든 데이터 항목을 조회합니다 (페이지네이션 지원)."""
        try:
            with self.get_db() as db:
                stmt = select(CollectedDataDB).offset(skip).limit(limit).order_by(CollectedDataDB.collected_at.desc())
                results = db.execute(stmt).scalars().all()
                return [self._map_db_to_pydantic(db_data) for db_data in results]
        except SQLAlchemyError as e:
            logger.error(f"Failed to get all data: {e}", exc_info=True)
            return []

    async def find_data(self, query: Dict[str, Any], limit: int = 100, skip: int = 0) -> List[CollectedData]:
         """주어진 쿼리 조건에 맞는 데이터 항목들을 조회합니다. (단순 동등 비교)"""
         try:
             with self.get_db() as db:
                 stmt = select(CollectedDataDB)
                 for key, value in query.items():
                     if hasattr(CollectedDataDB, key):
                         # Enum 타입 필터링 시 value 사용
                         if isinstance(value, (SourceType, ProcessingStatus)):
                             stmt = stmt.where(getattr(CollectedDataDB, key) == value.value)
                         else:
                             stmt = stmt.where(getattr(CollectedDataDB, key) == value)
                     elif key == 'extra_data': # extra_data 필터링 (JSON 필드)
                         # TODO: JSON 필드 검색 로직 구현 (DB에 따라 다름)
                         # 예: PostgreSQL의 경우 `CollectedDataDB.extra_data['some_key'] == 'some_value'`
                         # SQLite는 기본적으로 JSON 연산자를 지원하지 않을 수 있음.
                         logger.warning(f"Filtering by 'extra_data' is not fully supported in SQLiteRepository.")
                         pass # SQLite에서는 단순 문자열 비교 등 제한적 구현 가능
                     else:
                         logger.warning(f"Invalid query key: {key}")
                 stmt = stmt.offset(skip).limit(limit).order_by(CollectedDataDB.collected_at.desc())
                 results = db.execute(stmt).scalars().all()
                 return [self._map_db_to_pydantic(db_data) for db_data in results]
         except SQLAlchemyError as e:
             logger.error(f"Failed to find data with query {query}: {e}", exc_info=True)
             return []

    async def update_data(self, data_id: str, update_data: Dict[str, Any]) -> Optional[CollectedData]:
        """특정 ID의 데이터 항목을 업데이트합니다."""
        valid_keys = {field for field in CollectedData.model_fields if field != 'id'}
        filtered_update_data = {}
        for k, v in update_data.items():
            if k in valid_keys:
                # Enum 값은 value로 변환하여 저장
                if isinstance(v, (SourceType, ProcessingStatus)):
                    filtered_update_data[k] = v.value
                else:
                    filtered_update_data[k] = v

        if not filtered_update_data:
            logger.warning(f"No valid fields to update for ID {data_id}")
            return await self.get_data_by_id(data_id)

        try:
            with self.get_db() as db:
                stmt = (
                    update(CollectedDataDB)
                    .where(CollectedDataDB.id == data_id)
                    .values(**filtered_update_data)
                    # .returning(CollectedDataDB) # SQLite에서 returning 지원 불확실
                )
                result = db.execute(stmt)
                db.commit()

                if result.rowcount == 0:
                    logger.warning(f"Data ID not found for update: {data_id}")
                    return None
                
                # 업데이트 후 다시 조회하여 반환
                updated_db_data = db.get(CollectedDataDB, data_id) 
                if updated_db_data:
                     logger.debug(f"Updated data for ID: {data_id}")
                     return self._map_db_to_pydantic(updated_db_data)
                else:
                     # 업데이트는 성공했지만 조회 실패? (이론상 드묾)
                     logger.error(f"Failed to retrieve updated data for ID {data_id} after update.")
                     return None
        except SQLAlchemyError as e:
             logger.error(f"Failed to update data for ID {data_id}: {e}", exc_info=True)
             return None


    async def delete_data(self, data_id: str) -> bool:
        """특정 ID의 데이터 항목을 삭제합니다."""
        try:
            with self.get_db() as db:
                stmt = delete(CollectedDataDB).where(CollectedDataDB.id == data_id)
                result = db.execute(stmt)
                db.commit()
                deleted_count = result.rowcount
                if deleted_count > 0:
                    logger.debug(f"Deleted data for ID: {data_id}")
                    return True
                else:
                    logger.warning(f"Data ID not found for delete: {data_id}")
                    return False
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete data for ID {data_id}: {e}", exc_info=True)
            return False

    async def check_title_exists(self, title: str, threshold: float = 0.8) -> bool:
        """주어진 제목과 유사한 제목이 이미 저장소에 있는지 확인합니다."""
        if not title:
            return False

        # SQLite는 효율적인 유사도 검색 기능이 부족하므로,
        # 최근 N개의 데이터를 가져와 비교하거나, 제목이 null이 아닌 모든 데이터를 가져와 비교.
        # 성능 문제가 발생할 수 있으므로 주의 필요. 여기서는 모든 non-null 제목과 비교.
        try:
             with self.get_db() as db:
                 # 제목이 있는 모든 데이터 조회 (메모리 주의)
                 # TODO: 성능 개선 - DB 레벨에서 유사도 검색 지원하는 DB 사용 고려 또는 인덱싱 전략 변경
                 stmt = select(CollectedDataDB.title).where(CollectedDataDB.title.isnot(None))
                 existing_titles = db.execute(stmt).scalars().all()

                 for existing_title in existing_titles:
                     if is_title_duplicate(title, existing_title, threshold):
                         logger.debug(f"Found similar title for '{title}' (Existing: '{existing_title}', Threshold: {threshold})")
                         return True
                 return False
        except SQLAlchemyError as e:
             logger.error(f"Failed to check title existence for '{title}': {e}", exc_info=True)
             # 에러 발생 시 중복이 아니라고 가정 (정책 결정 필요)
             return False
        except Exception as e: # is_title_duplicate 등 다른 예외
             logger.error(f"An unexpected error occurred during title check for '{title}': {e}", exc_info=True)
             return False


# 전역 저장소 인스턴스 (설정에 따라 생성되도록 변경 가능)
# 예를 들어, app/repository/__init__.py 에서 설정에 따라 인스턴스 생성
# from app.config import DATA_STORAGE_TYPE
# if DATA_STORAGE_TYPE == 'sqlite':
#     data_store: BaseRepository = SQLiteRepository()
# else:
#     data_store: BaseRepository = InMemoryDataStore()

# 우선 SQLite 인스턴스를 기본으로 생성
# 실제 앱에서는 DI(Dependency Injection) 사용 권장
sqlite_store: BaseRepository = SQLiteRepository() 
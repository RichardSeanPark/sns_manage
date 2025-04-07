# SQLiteRepository 테스트 계획

이 문서는 `app.repository.sqlite_store.SQLiteRepository` 클래스의 기능 검증을 위한 테스트 계획 및 진행 상황을 기록합니다.

## 기능: SQLite 기반 데이터 저장소

- [x] SQLAlchemy 모델 정의 (`app/models/db_models.py`)
- [x] SQLite 데이터베이스 경로 설정 (`app/config.py`)
- [x] `BaseRepository` 상속 및 `SQLiteRepository` 구현 (`app/repository/sqlite_store.py`)
    - [x] 데이터베이스 초기화 및 테이블 생성 로직
    - [x] Pydantic 모델과 SQLAlchemy 모델 간 매핑 로직
    - [x] 데이터 CRUD (생성, 조회, 업데이트, 삭제) 메소드 구현
    - [x] 제목 유사도 기반 중복 저장 방지 로직 (`save_data` 내)
    - [x] 벌크 데이터 저장 메소드 구현 (`save_bulk_data`)
    - [x] 제목 존재 여부 확인 메소드 구현 (`check_title_exists`)
- [x] 전역 저장소 인스턴스를 `SQLiteRepository`로 변경 (`app/repository/data_store.py`)

## 테스트: SQLiteRepository

- [x] **데이터 저장 (save_data)**
    - [x] `test_save_data_success`: 유효한 데이터 저장 성공 확인
    - [x] `test_save_data_duplicate_id`: 동일 ID 중복 저장 시 `IntegrityError` 발생 및 `None` 반환 확인
    - [x] `test_save_data_duplicate_title`: 제목 중복 감지 및 저장 건너뛰기 (None 반환) 확인
    - [x] `test_save_data_similar_title_below_threshold`: 임계값 이하 유사도 제목 저장 성공 확인
- [x] **데이터 조회 (get_data_by_id)**
    - [x] `test_get_data_by_id`: 유효 ID로 데이터 조회 성공 확인
    - [x] `test_get_data_by_id_not_found`: 존재하지 않는 ID 조회 시 `None` 반환 확인
- [x] **데이터 전체 조회 및 검색 (get_all_data, find_data)**
    - [x] `test_get_all_data`: 페이지네이션 포함 전체 데이터 조회 확인
    - [x] `test_find_data`: 특정 조건 검색 결과 확인
- [x] **데이터 업데이트 (update_data)**
    - [x] `test_update_data`: 데이터 업데이트 성공 및 반영 확인
    - [x] `test_update_data_not_found`: 존재하지 않는 ID 업데이트 시 `None` 반환 확인
- [x] **데이터 삭제 (delete_data)**
    - [x] `test_delete_data`: 데이터 삭제 성공 및 반영 확인
    - [x] `test_delete_data_not_found`: 존재하지 않는 ID 삭제 시 `False` 반환 확인
- [x] **벌크 저장 (save_bulk_data)**
    - [x] `test_save_bulk_data`: 여러 데이터 동시 저장 및 결과 확인
- [x] **제목 존재 확인 (check_title_exists)**
    - [x] `test_check_title_exists`: 정확한 제목, 유사 제목(임계값 이하), 다른 제목, 제목 없는 데이터에 대한 결과 확인
- [x] **기타**
    - [x] `test_empty_database`: 초기 빈 데이터베이스 상태 확인 
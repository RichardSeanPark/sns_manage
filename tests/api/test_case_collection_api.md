# 수집 API (Collection API) 테스트 계획

이 문서는 `app.api.v1.collection` 모듈에 정의된 API 엔드포인트의 기능 검증을 위한 테스트 계획 및 진행 상황을 기록합니다.

## 기능: 수집 데이터 조회 API

- [x] API 라우터 생성 및 등록 (`app/api/v1/collection.py`, `app/main.py`)
- [x] `GET /api/v1/data/`: 수집된 데이터 목록 조회 엔드포인트 구현
  - [x] 페이지네이션 (`skip`, `limit`) 기능
  - [x] 저장소 (`SQLiteRepository.get_all_data`) 연동
- [ ] (TODO) `GET /api/v1/data/{item_id}`: 특정 ID 데이터 조회 엔드포인트 구현

## 테스트: GET /api/v1/data/

- [x] `test_read_collected_data_success`: 데이터가 있을 때 정상적으로 목록을 반환하는지 확인
  - [x] 기본 파라미터 (`skip=0`, `limit=100`)로 요청 시 상태 코드 200 확인
  - [x] 반환된 데이터가 리스트 형태인지 확인
  - [x] 반환된 각 항목이 `CollectedData` Pydantic 모델 형식인지 확인
  - [x] 테스트용 데이터가 포함되어 있는지 확인 (저장소 모의(mock) 필요)
- [x] `test_read_collected_data_pagination`: 페이지네이션이 올바르게 작동하는지 확인
  - [x] `limit` 파라미터로 반환되는 항목 수 제한 확인
  - [x] `skip` 파라미터로 조회 시작 위치 변경 확인
  - [x] `skip`과 `limit` 조합 테스트
- [x] `test_read_collected_data_empty`: 데이터가 없을 때 빈 리스트를 반환하는지 확인
  - [x] 저장소가 빈 데이터를 반환하도록 모의 설정
  - [x] API 요청 시 상태 코드 200 및 빈 리스트(`[]`) 반환 확인
- [x] `test_read_collected_data_invalid_limit`: `limit` 파라미터 제약 조건 확인 (예: `le=1000`)
  - [x] 허용된 최대 `limit` 값 초과 시 422 Unprocessable Entity 오류 확인
- [x] `test_read_collected_data_repository_error`: 저장소 조회 중 오류 발생 시 500 Internal Server Error 반환 확인
  - [x] 저장소 `get_all_data` 메소드가 예외를 발생시키도록 모의 설정
  - [x] API 요청 시 상태 코드 500 및 오류 메시지 확인

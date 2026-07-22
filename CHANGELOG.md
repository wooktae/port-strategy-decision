# CHANGELOG

## 2026-07-01

### Added

- README에 Decision 책임 경계, AWS 운영 구조에서의 Decision 위치, 컨테이너 이미지 섹션을 추가했다.
- README 실행 예시를 `python -m port_strategy_decision.xxx` 형식으로 정정해 Dockerfile CMD 및 실제 import 구조와 맞췄다.
- `docs/source-file-catalog.md`에 `Dockerfile`, `requirements.txt` 항목과 파일별 실행 위험 요약을 추가했다.
- `docs/worklog/2026-07-01.md`에 이번 문서 최신화 작업 기록을 추가했다.

### Changed

- AWS Paper Daily Step 6 Daily Buy Signal에서 Decision이 담당하는 진입점을 `daily_buy_signal_run.py` 기준으로 문서화했다.
- AWS Paper Daily Step 7 Position Signal에서 Decision이 담당하는 진입점을 `daily_position_signal_run.py`와 v1/v2 evaluator 기준으로 문서화했다.
- Decision과 Preprocessor, StrategyExecution, MarketConnector, View, StrategyResearch, Scheduler/Step Functions 사이의 실행 책임 경계를 README에 정리했다.

### Notes

- 실제 daily signal 실행, backtest/research 실행, execution order 생성, DB DDL/DML, 외부 API 호출, 크롤링, 주문 실행은 수행하지 않았다.
- port-view/.kiro 하위 View, MarketConnector, Crawler, Preprocessor, StrategyExecution, StrategyResearch, Scheduler, Lambda, Step Functions 세부 운영 로그는 이 저장소 문서 범위 밖으로 판단해 반영하지 않았다.
- 실제 cluster 이름, task definition ARN, image URI, subnet, security group, command id, IAM role ARN, secret ARN, DB host/port/user/password, 계좌번호 전체값, broker order number 전체값은 문서에 원문으로 기록하지 않았다.
- 코드/설정 파일 변경 없이 md 문서만 갱신했다.

## 2026-05-28

### Added

- 전체 파일 역할과 운영 주의사항을 정리한 `docs/source-file-catalog.md`를 추가했다.
- Python 소스 파일에 모듈 단위 한글 docstring과 핵심 파이프라인/DB 함수 설명을 추가했다.
- `docs/worklog/2026-05-28.md`에 이번 문서화/주석 정리 작업 기록을 추가했다.

### Changed

- `backtest_decision_run.py`에서 Common run store 의존성과 run 기록 생성 호출을 제거하고, 단일 일자 market/filter/sizing snapshot 출력 entrypoint로 정리했다.
- README와 `docs/source-file-catalog.md`에 `backtest_decision_run.py`가 run id를 출력하지 않고 DB feature 조회 기반 snapshot만 출력한다는 내용을 반영했다.
- README에 파일 카탈로그 위치와 문서화/주석 정리 시 기능 로직을 변경하지 않는 원칙을 보강했다.
- 기존 파일 상단의 로컬 절대 경로 주석은 모듈 역할 설명 docstring으로 대체했다.

### Notes

- 기능 변경 없음.
- 실제 DB 접속, daily signal 실행, backtest/research 실행, execution order 생성, 외부 API 호출, 크롤링, 주문 실행은 수행하지 않았다.
- 민감정보 값은 문서와 주석에 기록하지 않았다.

## 2026-05-27

### Changed

- DB 접속 설정을 로컬 `db_config.py`의 `get_db_config()`로 외부화하고 `INTEREST_DB_*` 환경변수 기반으로 정리했다.
- password 하드코딩 후보를 제거하고 `INTEREST_DB_PASSWORD` 필수 검증으로 변경했다.
- 로컬 PostgreSQL 기본 DB명을 `interest_crawler`에서 `portfolio`로 변경한 내용을 문서에 반영했다.
- AWS Migration 준비 관점의 단일 DB `portfolio` + schema-per-domain 구조와 decision 모듈 `search_path`를 문서화했다.
- schema-per-domain 전환 후에도 기존 SQL은 `search_path` 기반으로 동작한다는 설명을 추가했다.

### Notes

- 실제 DB 접속, daily signal 실행, backtest/research 실행, execution order 생성, 외부 API 호출, 크롤링, 주문 실행은 수행하지 않았다.
- 민감정보 값은 문서에 기록하지 않았다.

## 2026-05-26

### Added

- 초기 프로젝트 문서 초안을 추가했다.
  - `AGENTS.md`
  - `README.md`
  - `docs/worklog/2026-05-26.md`

### Removed

- ignored 상태의 로컬 test/debug 후보 파일 9개와 Python 캐시 산출물 `__pycache__/`를 정리했다.
  - `test_compare_common_buy_filter.py`
  - `test_compare_common_buy_sizing.py`
  - `test_compare_common_buy_toxic_guard.py`
  - `test_compare_common_market.py`
  - `test_compare_common_sell_logic.py`
  - `test_compare_daily_position_v1_v2.py`
  - `test_daily_buy_toxic_haircut.py`
  - `test_daily_position_v1_v2_synthetic.py`
  - `test_debug_daily_buy_toxic.py`
- 보류 대상으로 분류한 `backtest_decision_run.py`, `daily_validator.py`는 삭제하지 않았다.

### Notes

- 현재 로컬 파일 구조와 스크립트 import/entrypoint 확인 결과를 기준으로 작성했다.
- 실제 daily signal 실행, backtest/research 실행, execution order 생성, DB DDL/DML, 외부 API 호출, 크롤링, 주문 실행은 수행하지 않았다.
- 민감정보 값은 문서에 기록하지 않았다.

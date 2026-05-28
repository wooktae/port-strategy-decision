# Source File Catalog

이 문서는 `port_strategy_decision` 루트 기준 주요 소스/문서 파일의 역할을 정리한 것이다. build 결과물, cache, IDE 임시 파일, `__pycache__` 같은 생성물은 제외한다.

## Python 소스

### `__init__.py`
- 한글 제목: 패키지 초기화 파일
- 파일 내용: 루트 스크립트를 `port_strategy_decision` 패키지 경로로 import할 수 있게 하는 초기화 파일이다.
- 주요 역할: daily/backtest 계열 모듈의 import 경로 기준점 역할을 한다.
- 수정/운영 시 주의사항: 기능 로직은 없지만 패키지 import에 영향을 줄 수 있으므로 삭제하지 않는다.

### `backtest_decision_run.py`
- 한글 제목: 단일 일자 decision snapshot 실행 후보
- 파일 내용: market/stock feature를 DB에서 읽고 market/filter/sizing 결과와 run id를 출력한다.
- 주요 역할: `backtest_market.py`, `backtest_filter.py`, `backtest_sizing.py` adapter를 묶어 단일 일자 판단 흐름을 확인한다.
- 수정/운영 시 주의사항: DB 접근과 run 기록 생성 가능성이 있으므로 문서화 작업 중 실행하지 않는다. backtest/research 금지 범위에 포함된다.

### `backtest_filter.py`
- 한글 제목: 매수 후보 필터 adapter
- 파일 내용: stock feature 목록과 market decision을 공통 buy filter 입력으로 변환한다.
- 주요 역할: `port_strategy_common.common_buy_filter.common_filter_buy_candidates` 호출을 decision 계층에서 재사용한다.
- 수정/운영 시 주의사항: 공통 필터 config, decision reason 문자열, 후보 row 필드 계약을 변경하지 않는다.

### `backtest_market.py`
- 한글 제목: 시장 판단 adapter
- 파일 내용: market feature row를 공통 market context로 변환하고 decision 계층의 `MarketDecision`을 반환한다.
- 주요 역할: `port_strategy_common.common_market.common_decide_market`을 daily/backtest 흐름에 연결한다.
- 수정/운영 시 주의사항: `MarketDecision` 필드명과 common market config 계약을 유지한다.

### `backtest_sizing.py`
- 한글 제목: 포지션 sizing adapter
- 파일 내용: 매수 후보와 market decision을 공통 sizing 입력으로 변환한다.
- 주요 역할: `port_strategy_common.common_buy_sizing.common_allocate_positions` 호출 결과를 그대로 사용한다.
- 수정/운영 시 주의사항: position size 의미와 `SIZING_CONFIG` 계약을 바꾸지 않는다.

### `daily_block_watch_builder.py`
- 한글 제목: BLOCK watch 후보 builder
- 파일 내용: BLOCK 시장 구간에서 강한 예외 후보를 관찰 후보 dict로 변환한다.
- 주요 역할: `evaluate_block_watch_candidate` 결과를 `strategy_block_watch_candidate` 저장 형식으로 맞춘다.
- 수정/운영 시 주의사항: BUY signal이나 execution order를 만들지 않는 보조 흐름이라는 점을 유지한다.

### `daily_block_watch_repository.py`
- 한글 제목: BLOCK watch 후보 repository
- 파일 내용: `strategy_block_watch_candidate` 저장과 daily run별 삭제를 담당한다.
- 주요 역할: BLOCK 구간 관찰 후보를 upsert하고 재실행 시 오래된 후보를 정리한다.
- 수정/운영 시 주의사항: DB 쓰기 함수이므로 호출 entrypoint 실행 전 transaction 범위와 upsert key를 확인한다.

### `daily_buy_signal_run.py`
- 한글 제목: daily BUY signal 생성 entrypoint
- 파일 내용: feature 조회, market/filter/sizing, BUY signal 저장, BLOCK watch 저장, run 상태 갱신을 수행한다.
- 주요 역할: daily buy signal 계열의 전체 파이프라인을 orchestration한다.
- 수정/운영 시 주의사항: DB 쓰기와 run 상태 갱신이 포함된다. 실제 daily signal 실행, 주문 후보 생성으로 이어질 수 있는 운영 흐름은 승인 없이 실행하지 않는다.

### `daily_feature_loader.py`
- 한글 제목: daily feature loader
- 파일 내용: run date/data date를 결정하고 market/stock feature를 DB에서 조회한다.
- 주요 역할: `pre_total_market_daily_feature`, `pre_total_stock_daily_feature`, `stock_universe`를 daily signal 입력으로 제공한다.
- 수정/운영 시 주의사항: 입력 feature 테이블명과 data date 결정 방식은 daily buy signal 계약에 직접 연결된다.

### `daily_position_evaluator.py`
- 한글 제목: daily position v1 evaluator
- 파일 내용: 보유 포지션을 HOLD/SELL/SKIP으로 판단하는 v1 로직을 저장용 dict로 만든다.
- 주요 역할: hard stop, 최소/최대 보유일, market BLOCK, 품질 저하, 수익권 HOLD 기준을 적용한다.
- 수정/운영 시 주의사항: 기존 운영 SELL v1과 맞춘 reason/status 문자열을 유지한다. DB 쓰기와 주문 생성은 하지 않는다.

### `daily_position_evaluator_v2.py`
- 한글 제목: daily position v2 evaluator
- 파일 내용: daily 운영 검증을 먼저 처리하고 common sell 판단 결과를 daily decision 형식으로 변환한다.
- 주요 역할: `common_evaluate_backtest_sell`을 daily position 판단에 재사용한다.
- 수정/운영 시 주의사항: daily hard stop 선처리, common sell mapping, reason 문자열 계약을 변경하지 않는다.

### `daily_position_repository.py`
- 한글 제목: daily position repository
- 파일 내용: active position, broker snapshot, feature 조회와 daily position decision 저장을 담당한다.
- 주요 역할: `strategy_daily_position_decision` upsert와 `strategy_position_state` latest 평가 갱신을 수행한다.
- 수정/운영 시 주의사항: DB 쓰기가 포함된다. table/column/unique key/upsert 정책과 broker snapshot 조회 기준을 유지한다.

### `daily_position_signal_run.py`
- 한글 제목: daily position decision entrypoint
- 파일 내용: 최신 완료 daily run과 활성 포지션을 읽어 v1/v2 evaluator로 HOLD/SELL/SKIP 판단을 생성한다.
- 주요 역할: daily position signal 계열의 조회, 평가, 저장, 요약 출력을 orchestration한다.
- 수정/운영 시 주의사항: DB 쓰기와 position state latest 갱신이 포함되므로 운영 승인 없이 실행하지 않는다.

### `daily_repository.py`
- 한글 제목: daily buy signal repository
- 파일 내용: `strategy_daily_run`, `strategy_daily_signal` 생성/갱신/조회 함수를 제공한다.
- 주요 역할: daily run lifecycle과 BUY signal upsert를 담당한다.
- 수정/운영 시 주의사항: unique key, run status, signal status, upsert 정책을 유지한다.

### `daily_signal_builder.py`
- 한글 제목: daily BUY signal builder
- 파일 내용: sizing 결과와 stock feature를 `strategy_daily_signal` 저장 row로 변환한다.
- 주요 역할: feature snapshot, buy_info, raw_features, entry_reason을 구성한다.
- 수정/운영 시 주의사항: `signal_type=BUY`, `signal_status=READY`, reason 문자열과 source table 값을 변경하지 않는다.

### `daily_validator.py`
- 한글 제목: latest daily run 검증 조회 도구
- 파일 내용: 최신 daily run과 연결된 daily signal을 조회해 콘솔에 출력한다.
- 주요 역할: daily buy signal 저장 결과를 사람이 확인할 수 있게 출력한다.
- 수정/운영 시 주의사항: DB 조회와 운영 데이터 출력이 포함되므로 실행 전 민감정보 노출 가능성을 확인한다.

### `db_config.py`
- 한글 제목: DB 접속 설정 모듈
- 파일 내용: `INTEREST_DB_*` 환경변수에서 PostgreSQL 접속 정보를 읽고 search_path를 설정한다.
- 주요 역할: decision 모듈의 `psycopg2.connect` 설정을 중앙화한다.
- 수정/운영 시 주의사항: password 기본값을 두지 않는다. 민감정보 값은 문서/로그에 쓰지 않고 환경변수 또는 로컬 설정에서 주입한다.

## 문서 파일

### `AGENTS.md`
- 한글 제목: 작업 지침 문서
- 파일 내용: 이 저장소의 작업 범위, 금지 작업, 보안, Git, 검증, 문서화 규칙을 정의한다.
- 주요 역할: AWS Migration 전 정리 작업에서 변경 가능 범위와 운영 안전 제약을 명확히 한다.
- 수정/운영 시 주의사항: 실제 운영 실행 금지와 민감정보 미기록 원칙을 약화하지 않는다.

### `README.md`
- 한글 제목: 프로젝트 개요 문서
- 파일 내용: daily decision 계층의 역할, 구조, 실행/설정 방법, 의존성, 안전 제약을 설명한다.
- 주요 역할: 신규 작업자가 모듈 구조와 실행 위험을 빠르게 파악하도록 돕는다.
- 수정/운영 시 주의사항: 실행 예시는 형식만 제공하고 실제 credential, 계좌번호, 운영 값은 기록하지 않는다.

### `CHANGELOG.md`
- 한글 제목: 변경 이력 문서
- 파일 내용: 날짜별 주요 변경, 문서화, 기능 변경 여부를 요약한다.
- 주요 역할: 마이그레이션 전 정리 작업과 기능 영향 여부를 추적한다.
- 수정/운영 시 주의사항: 실제 변경된 내용만 짧게 기록하고 기능 변경이 없으면 명시한다.

### `docs/source-file-catalog.md`
- 한글 제목: 전체 파일 내용 정리 문서
- 파일 내용: 루트 기준 주요 소스/문서 파일별 역할, 책임, 운영 주의사항을 정리한다.
- 주요 역할: AWS Migration 전 모듈 구성과 위험 실행 지점을 한눈에 확인하게 한다.
- 수정/운영 시 주의사항: unused/legacy 의심 파일은 삭제하지 말고 “정리 후보”로만 표시한다.

### `docs/worklog/2026-05-26.md`
- 한글 제목: 2026-05-26 작업 기록
- 파일 내용: 초기 문서 초안 작성, 파일 구조 확인, 로컬 산출물 정리 내용을 기록한다.
- 주요 역할: 초기 정리 작업의 계획/완료/확인 상태를 보존한다.
- 수정/운영 시 주의사항: 기존 들여쓰기와 상태 표기 형식을 유지한다.

### `docs/worklog/2026-05-27.md`
- 한글 제목: 2026-05-27 작업 기록
- 파일 내용: DB 설정 외부화, schema-per-domain 문서 반영, 안전 제약 확인을 기록한다.
- 주요 역할: 어제 작업의 미커밋 변경 요약 근거로 사용된다.
- 수정/운영 시 주의사항: 실제 DB 접속값이나 민감정보 값을 기록하지 않는다.

### `docs/worklog/2026-05-28.md`
- 한글 제목: 2026-05-28 작업 기록
- 파일 내용: 미커밋 상태 확인, 전체 파일 카탈로그 작성, 파일별 설명 주석 추가를 기록한다.
- 주요 역할: 이번 AWS Migration 전 정리 작업의 완료 범위와 검증 결과를 남긴다.
- 수정/운영 시 주의사항: 문서/주석 변경 중심으로 기록하고 기능 변경이 없음을 명시한다.

## 정리 후보

현재 tracked 파일 중 삭제 대상으로 확정할 unused/legacy 파일은 없다. `backtest_decision_run.py`와 `daily_validator.py`는 실행 위험이 있는 후보성 도구지만 삭제 대상이 아니며, 운영 승인 없이 실행하지 않는 파일로 분류한다.

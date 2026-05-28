# port_strategy_decision

포트폴리오 전략의 daily decision 계층을 담당하는 Python 마이크로서비스 루트다. 전처리 계층이 만든 total feature를 읽어 시장 판단, 매수 후보 필터, sizing, daily buy signal, 보유 포지션 HOLD/SELL 판단을 생성한다.

이 문서는 현재 로컬 파일 구조와 import/entrypoint 확인 결과를 기준으로 작성했다. 실제 daily signal 실행, backtest/research 실행, execution order 생성, DB DDL/DML, 외부 API 호출, 크롤링, 주문 실행은 수행하지 않았다.

## 현재 구조

현재 루트는 패키지 디렉터리보다 독립 실행형 Python 스크립트 중심이다.

- daily buy signal 계열
  - `daily_buy_signal_run.py`: `pre_total_*` feature를 읽어 시장 판단, 매수 후보 필터, sizing, BUY signal, BLOCK watch 후보 저장을 묶는 daily buy signal entrypoint 후보.
  - `daily_feature_loader.py`: run date와 data date를 결정하고 `pre_total_market_daily_feature`, `pre_total_stock_daily_feature`, `stock_universe`에서 feature를 조회하는 loader.
  - `daily_signal_builder.py`: sizing 결과와 stock feature를 `strategy_daily_signal` 저장 형식으로 변환.
  - `daily_repository.py`: `strategy_daily_run`, `strategy_daily_signal` 생성, 갱신, 조회 repository.
  - `daily_block_watch_builder.py`: BLOCK 시장 구간에서 BUY signal은 만들지 않고 관찰 후보만 선별.
  - `daily_block_watch_repository.py`: `strategy_block_watch_candidate` 계열 저장/삭제 repository.
- daily position signal 계열
  - `daily_position_signal_run.py`: 최신 완료 daily run과 활성 포지션을 읽어 v1/v2 evaluator로 HOLD/SELL/SKIP decision을 생성하는 entrypoint 후보.
  - `daily_position_evaluator.py`: daily position v1 판단. 운영 SELL v1 기준과 맞춘 hard stop, 최소/최대 보유일, market BLOCK, 품질 저하, 수익권 HOLD 판단을 수행.
  - `daily_position_evaluator_v2.py`: daily position v2 판단. daily 운영 검증을 먼저 처리하고 `port_strategy_common.common_sell_decision.common_evaluate_backtest_sell`을 재사용.
  - `daily_position_repository.py`: active position, broker position snapshot, stock/market feature, daily position decision 저장 및 position state latest 평가 갱신 repository.
- market/filter/sizing/decision 계열
  - `backtest_market.py`: `port_strategy_common.common_market.common_decide_market`을 호출해 `MarketDecision`으로 변환하는 market decision adapter.
  - `backtest_filter.py`: `port_strategy_common.common_buy_filter.common_filter_buy_candidates`를 호출하는 buy candidate filter adapter.
  - `backtest_sizing.py`: `port_strategy_common.common_buy_sizing.common_allocate_positions`를 호출하는 sizing adapter.
  - `backtest_decision_run.py`: 단일 일자 market/stock feature를 읽어 market/filter/sizing decision snapshot만 출력하는 backtest 성격 entrypoint 후보. 실제 실행 시 DB feature 조회가 발생하므로 문서화 작업 중 실행하지 않는다.
- 검증/조회 후보
  - `daily_validator.py`: 최신 daily run과 signal을 조회해 출력하는 검증 후보. DB 조회와 민감정보 출력 가능성을 확인한 뒤에만 실행한다.
- 로컬 산출물 또는 후보
  - test/debug/output dump로 보이는 파일은 운영 소스로 단정하지 않고 후보 또는 로컬 산출물로만 취급한다.

전체 파일별 역할, DB 접근 지점, 실행 주의사항은 `docs/source-file-catalog.md`에 별도로 정리했다. AWS Migration 전 초기 정리에서는 이 문서를 기준으로 unused/legacy 의심 파일을 삭제하지 않고 “정리 후보”로만 표시한다.

## 주요 기능

- total market feature 기반 market signal, base exposure, max positions, min score/flow 판단
- total stock feature 기반 buy candidate filter와 position sizing
- daily BUY signal 저장 및 daily run 성공/실패 상태 갱신
- BLOCK 시장에서 강한 예외 후보를 별도 watch candidate로 기록
- 최신 완료 daily run 기준 보유 포지션 HOLD/SELL/SKIP 판단
- broker position snapshot, strategy position state, stock/market feature를 결합한 daily position decision 생성
- v2 evaluator에서 common sell 판단을 daily 계층에 맞게 adapter 처리

## port_strategy_common 의존성

이 저장소는 판단 핵심 로직 상당 부분을 `port_strategy_common`에서 가져온다.

- `port_strategy_common.config`
  - `STRATEGY_NAME`, `ENGINE_VERSION`, `MARKET_CONFIG`, `FILTER_CONFIG`, `SIZING_CONFIG`, `DECISION_RUN_DATE`, `get_config_snapshot`을 참조한다.
- `db_config.py`
  - 이 MS의 DB 접속 설정은 `INTEREST_DB_*` 환경변수에서 읽는다.
- market decision
  - `backtest_market.py`가 `CommonMarketContext`를 만들고 `common_decide_market`을 호출한다.
- buy filter
  - `backtest_filter.py`가 `CommonMarketDecision`으로 변환한 뒤 `common_filter_buy_candidates`를 호출한다.
- sizing
  - `backtest_sizing.py`가 `common_allocate_positions`를 호출한다.
  - `daily_buy_signal_run.py`는 buy guard와 haircut에 `common_decide_buy_guard`, `common_apply_backtest_buy_size_haircut`, `common_safe_float`를 사용한다.
- run store
  - `backtest_decision_run.py`는 더 이상 Common run store를 참조하지 않고, snapshot 출력용으로만 유지한다.
- block watch
  - `daily_block_watch_builder.py`가 `evaluate_block_watch_candidate`를 사용한다.
- sell decision
  - `daily_position_evaluator_v2.py`가 `common_evaluate_backtest_sell`을 daily position decision 형식으로 mapping한다.

공통 로직 함수명, dataclass 필드, decision reason 문자열은 다른 서비스와 연결될 수 있으므로 명시 요청 없이 변경하지 않는다.

## 실행 방법

각 스크립트는 독립 실행형 entrypoint를 가진 파일이 있다. 다만 실행 시 DB 연결, signal/decision upsert, position state 갱신, 주문 후보로 이어질 수 있는 데이터 생성이 발생할 수 있으므로 운영 환경에서만 의도적으로 실행해야 한다.

예시 형식:

```powershell
python daily_buy_signal_run.py --run-date 2026-05-26 --data-date 2026-05-25
python daily_position_signal_run.py --evaluator-version v2
python daily_validator.py
```

문서화/분석 작업 중에는 위 명령을 실행하지 않는다. `backtest_decision_run.py`도 run 기록은 생성하지 않지만 DB feature 조회를 수행하므로 backtest/research 금지 범위에서는 실행하지 않는다.

## 설정 방법

설정은 주로 `port_strategy_common.config`와 로컬 `db_config.py`에서 가져온다. 민감정보는 코드, 문서, 로그, 예시 출력에 기록하지 않는다. 필요한 값은 환경변수 또는 local config로 분리하고 문서에는 `[REDACTED]`로 마스킹한다.

주요 설정 유형:

- PostgreSQL host, port, database, user, password
- strategy name과 engine version
- market/filter/sizing config
- decision run date
- feature 입력 테이블과 strategy 출력 테이블의 스키마 계약
- 계좌 필터 또는 broker position snapshot 조회 조건

DB 접속 환경변수:

```powershell
$env:INTEREST_DB_HOST="localhost"
$env:INTEREST_DB_PORT="5433"
$env:INTEREST_DB_NAME="portfolio"
$env:INTEREST_DB_USER="postgres"
$env:INTEREST_DB_PASSWORD="[REDACTED]"
```

`INTEREST_DB_NAME`의 기본 DB명은 `portfolio`다. 이 모듈에서는 현재 `INTEREST_DB_*` 환경변수를 사용하며, 같은 포트폴리오 시스템 내에서 `PORTFOLIO_DB_NAME` 계열 이름을 병행해 설명하는 경우에도 기본 DB명은 `portfolio`로 맞춘다. `INTEREST_DB_PASSWORD`는 기본값이 없으며 비어 있으면 실행 시 `RuntimeError`가 발생한다. 나머지 값은 위 예시 값이 기본값이다.

로컬 PostgreSQL은 AWS Migration 준비 관점에서 단일 DB `portfolio` 안에 domain별 schema를 나누는 구조를 사용한다. 이 모듈의 DB connection `search_path`는 다음 순서를 기준으로 한다.

```text
decision, research, preprocessor, execution, connector, reference, legacy, public
```

`public`에 있던 테이블은 domain schema로 이동되었지만, 기존 SQL은 schema-qualified table name을 강제하지 않고 위 `search_path` 기반으로 계속 동작하도록 유지한다. Daily BUY Signal은 `strategy_block_watch_candidate`를 사용하므로 `research` schema가 `search_path`에 포함되어야 한다.

민감정보는 환경변수 또는 로컬 운영 설정으로 관리한다. 문서에는 실제 password, token, account, webhook URL 값을 쓰지 않고 필요한 경우 `[REDACTED]`로 마스킹한다.

## 외부 의존성

현재 파일에서 확인되는 주요 의존성 후보는 다음과 같다.

- Python
- `psycopg2`
- `psycopg2.extras`
- PostgreSQL
- `port_strategy_common`
- 전처리 산출 테이블: `pre_total_market_daily_feature`, `pre_total_stock_daily_feature`
- 전략 출력 테이블: `strategy_daily_run`, `strategy_daily_signal`, `strategy_block_watch_candidate`, `strategy_daily_position_decision`, `strategy_position_state`
- broker snapshot 테이블: `connector_balance_snapshot`, `connector_position_snapshot`

## 안전 제약

- 실제 daily signal 실행 금지
- backtest/research 실행 금지
- execution/order 생성 실행 금지
- DB DDL/DML 직접 실행 금지
- 외부 API 호출 금지
- 크롤링 실행 금지
- 주문 실행 금지
- 민감정보 값 출력 또는 문서 기록 금지
- 민감정보가 필요하면 `[REDACTED]`로 마스킹
- test/debug/output dump 파일은 운영 소스로 단정하지 않고 후보 또는 로컬 산출물로만 표현
- 문서화/주석 정리 작업은 기능 로직, URL, endpoint, class/function signature, SQL 결과 의미, DB schema/table/column 이름, batch step 순서를 변경하지 않는다.
- Python 파일 상단 설명 주석은 실행 진입점, DB 접근, 외부 API 호출 여부를 이해하기 위한 설명으로만 유지한다.

## 검증

문서만 수정한 경우에는 변경 범위만 확인한다.

```powershell
git status --short
git diff --stat
```

코드 수정 시에도 실제 daily signal, backtest/research, execution/order 생성, DB 쓰기, 외부 API, 크롤링, 주문 실행이 포함되지 않는 검증만 선택한다. 실행 위험이 있으면 완료 보고에 검증 한계를 남긴다.

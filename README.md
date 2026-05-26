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
  - `backtest_decision_run.py`: 단일 일자 market/stock feature를 읽어 decision snapshot을 출력하는 backtest 성격 entrypoint 후보. 실제 실행 시 DB 접근과 run 기록 생성 가능성이 있으므로 문서화 작업 중 실행하지 않는다.
- 검증/조회 후보
  - `daily_validator.py`: 최신 daily run과 signal을 조회해 출력하는 검증 후보. DB 조회와 민감정보 출력 가능성을 확인한 뒤에만 실행한다.
- 로컬 산출물 또는 후보
  - test/debug/output dump로 보이는 파일은 운영 소스로 단정하지 않고 후보 또는 로컬 산출물로만 취급한다.

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
  - `DB_CONFIG`, `STRATEGY_NAME`, `ENGINE_VERSION`, `MARKET_CONFIG`, `FILTER_CONFIG`, `SIZING_CONFIG`, `DECISION_RUN_DATE`, `get_config_snapshot`을 참조한다.
- market decision
  - `backtest_market.py`가 `CommonMarketContext`를 만들고 `common_decide_market`을 호출한다.
- buy filter
  - `backtest_filter.py`가 `CommonMarketDecision`으로 변환한 뒤 `common_filter_buy_candidates`를 호출한다.
- sizing
  - `backtest_sizing.py`가 `common_allocate_positions`를 호출한다.
  - `daily_buy_signal_run.py`는 buy guard와 haircut에 `common_decide_buy_guard`, `common_apply_backtest_buy_size_haircut`, `common_safe_float`를 사용한다.
- block watch
  - `daily_block_watch_builder.py`가 `evaluate_block_watch_candidate`를 사용한다.
- sell decision
  - `daily_position_evaluator_v2.py`가 `common_evaluate_backtest_sell`을 daily position decision 형식으로 mapping한다.

공통 로직 함수명, dataclass 필드, decision reason 문자열은 다른 서비스와 연결될 수 있으므로 명시 요청 없이 변경하지 않는다.

## 실행 방법

각 스크립트는 독립 실행형 entrypoint를 가진 파일이 있다. 다만 실행 시 DB 연결, run 기록 생성, signal/decision upsert, position state 갱신, 주문 후보로 이어질 수 있는 데이터 생성이 발생할 수 있으므로 운영 환경에서만 의도적으로 실행해야 한다.

예시 형식:

```powershell
python daily_buy_signal_run.py --run-date 2026-05-26 --data-date 2026-05-25
python daily_position_signal_run.py --evaluator-version v2
python daily_validator.py
```

문서화/분석 작업 중에는 위 명령을 실행하지 않는다. `backtest_decision_run.py`도 DB 접근과 run 기록 생성 가능성이 있으므로 backtest/research 금지 범위에서는 실행하지 않는다.

## 설정 방법

설정은 주로 `port_strategy_common.config`에서 가져온다. 민감정보는 코드, 문서, 로그, 예시 출력에 기록하지 않는다. 필요한 값은 환경변수 또는 local config로 분리하고 문서에는 `[REDACTED]`로 마스킹한다.

주요 설정 유형:

- PostgreSQL host, port, database, user, password
- strategy name과 engine version
- market/filter/sizing config
- decision run date
- feature 입력 테이블과 strategy 출력 테이블의 스키마 계약
- 계좌 필터 또는 broker position snapshot 조회 조건

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

## 검증

문서만 수정한 경우에는 변경 범위만 확인한다.

```powershell
git status --short
git diff --stat
```

코드 수정 시에도 실제 daily signal, backtest/research, execution/order 생성, DB 쓰기, 외부 API, 크롤링, 주문 실행이 포함되지 않는 검증만 선택한다. 실행 위험이 있으면 완료 보고에 검증 한계를 남긴다.

# port_strategy_decision

`port_strategy_decision`은 Preprocessor가 생성한 total feature를 읽어 일일 전략 판단을 만드는 Decision 마이크로서비스다.

시장 상태와 매수 가능 범위를 판단하고, 종목 후보를 필터링해 수량을 계산한다. 또한 활성 포지션을 평가해 HOLD, SELL, SKIP 판단을 생성한다.

이 문서는 현재 저장소의 파일 구조, import, entrypoint와 기존 운영 문서를 기준으로 작성했다. 문서 정리 과정에서는 실제 daily signal, position signal, backtest, DB 쓰기, 외부 API, AWS와 주문 실행을 수행하지 않았다.

## 1. 서비스 요약

| 항목 | 값 |
|---|---|
| 서비스 | `port_strategy_decision` |
| 계층 | Daily Decision |
| 주요 입력 | `pre_total_market_daily_feature`, `pre_total_stock_daily_feature` |
| 주요 판단 | Market, Buy Filter, Sizing, BUY, BLOCK Watch, HOLD, SELL, SKIP |
| 주요 출력 | Daily Run, Daily Signal, Block Watch Candidate, Position Decision, Position State |
| 공통 로직 | `port_strategy_common` |
| 운영 진입점 | `daily_buy_signal_run.py`, `daily_position_signal_run.py` |
| 상세 파일 문서 | `docs/source-file-catalog.md` |

## 2. 책임 경계

Decision은 feature를 기반으로 판단 결과를 생성하고 저장한다. 원천 수집, feature 생성, 주문 실행과 화면 표시는 다른 계층의 책임이다.

### 2.1 Decision이 담당하는 범위

| 영역 | 책임 |
|---|---|
| Market | 시장 상태와 노출 한도, 최대 보유 수, 최소 점수·수급 기준 판단 |
| Buy Filter | 종목 feature를 매수 후보 기준으로 필터링 |
| Sizing | 후보별 매수 수량과 비중 계산 |
| Daily Buy | Daily Run과 BUY Signal 생성 및 실행 상태 갱신 |
| BLOCK Watch | BUY 차단 구간의 관찰 후보 별도 기록 |
| Position | 활성 포지션의 HOLD, SELL, SKIP 판단 |
| Adapter | `port_strategy_common` 결과를 daily 저장 형식으로 변환 |

### 2.2 다른 계층이 담당하는 범위

| 영역 | 담당 계층 |
|---|---|
| 외부 데이터 수집 | Crawler |
| raw 데이터 전처리와 total feature 생성 | Preprocessor |
| execution plan과 주문 요청 구성 | StrategyExecution |
| broker 주문·체결·잔고·보유 동기화 | MarketConnector |
| backtest 시나리오와 연구 보고서 | StrategyResearch |
| 상태 조회와 승인 UI | View |
| 전체 batch orchestration | EventBridge Scheduler와 Step Functions |
| 이미지 build, ECR push와 task definition 등록 | 배포 파이프라인 |

Decision이 SELL 판단을 만들더라도 실제 매도 주문을 제출하지 않는다. BUY Signal도 StrategyExecution이 소비하기 전까지는 주문이 아니다.

## 3. 핵심 실행 흐름

### 3.1 Daily Buy Signal

```text
Preprocessor total feature
  → Daily Feature Loader
  → Market Decision
  → Buy Candidate Filter
  → Position Sizing
  → BUY Signal 또는 BLOCK Watch
  → Daily Run 상태 갱신
```

| 단계 | 주요 파일 |
|---|---|
| 진입점 | `daily_buy_signal_run.py` |
| feature 조회 | `daily_feature_loader.py` |
| market 판단 | `backtest_market.py` |
| 후보 필터 | `backtest_filter.py` |
| 수량 계산 | `backtest_sizing.py` |
| signal 변환 | `daily_signal_builder.py` |
| run·signal 저장 | `daily_repository.py` |
| BLOCK 후보 선별 | `daily_block_watch_builder.py` |
| BLOCK 후보 저장 | `daily_block_watch_repository.py` |

Market이 BLOCK이면 일반 BUY Signal을 만들지 않고 관찰 후보만 별도 저장한다. BLOCK Watch는 주문 우회 경로가 아니라 관찰용 산출물이다.

### 3.2 Daily Position Signal

```text
Latest completed Daily Run
  + Active Strategy Position
  + Broker Position Snapshot
  + Market·Stock Feature
  → Position Evaluator v1 또는 v2
  → HOLD · SELL · SKIP Decision
  → Position State 최신 평가 갱신
```

| 단계 | 주요 파일 |
|---|---|
| 진입점 | `daily_position_signal_run.py` |
| v1 평가 | `daily_position_evaluator.py` |
| v2 평가 | `daily_position_evaluator_v2.py` |
| 입력 조회·결과 저장 | `daily_position_repository.py` |

v1은 daily 운영 기준을 직접 평가한다. v2는 daily 검증을 먼저 수행한 뒤 `port_strategy_common`의 sell 판단을 재사용해 daily decision 형식으로 변환한다.

### 3.3 조회와 보조 진입점

| 파일 | 현재 역할 |
|---|---|
| `backtest_decision_run.py` | 단일 일자 feature를 읽어 market, filter, sizing snapshot을 출력하는 보조 진입점 |
| `daily_validator.py` | 최신 Daily Run과 Signal을 조회해 확인하는 검증 후보 |

두 파일 모두 DB 조회가 발생할 수 있다. 문서 작업이나 단순 구조 점검 중에는 실행하지 않는다.

## 4. 입력 데이터

Decision은 원천 데이터를 직접 수집하거나 total feature를 생성하지 않는다.

| 입력 | 사용 목적 |
|---|---|
| `pre_total_market_daily_feature` | 시장 상태와 시장 단위 제한 판단 |
| `pre_total_stock_daily_feature` | 종목 필터, sizing과 position 평가 |
| `stock_universe` | 종목명(company_name) 보강용 LEFT JOIN 대상 |
| `connector_balance_snapshot` | Position 평가에서 최신 broker snapshot 기준일 확인 |
| `connector_position_snapshot` | broker 보유 상태 확인 |
| `strategy_position_state` | 전략 포지션의 최신 상태 확인 |

입력 데이터에서는 run date와 data date를 구분한다. Market과 Stock feature가 같은 판단 기준일을 가리키는지 확인해야 하며, 누락값과 실제 0값을 같은 의미로 처리하면 안 된다.

## 5. 출력 데이터

| 출력 | 의미 |
|---|---|
| `strategy_daily_run` | Daily Buy 판단 실행 단위와 최종 상태 |
| `strategy_daily_signal` | BUY 후보와 sizing 결과 |
| `strategy_block_watch_candidate` | BLOCK 시장의 관찰 후보 |
| `strategy_daily_position_decision` | 포지션 HOLD, SELL, SKIP 판단 이력 |
| `strategy_position_state` | 포지션의 최신 평가 상태 |

테이블명, 상태값, reason, evaluator version, unique key와 upsert 범위는 downstream 계약과 연결된다. 변경 시 StrategyExecution과 운영 조회 영향까지 함께 확인해야 한다.

## 6. 주요 파일 구조

### 6.1 Daily Buy 계열

| 파일 | 역할 |
|---|---|
| `daily_buy_signal_run.py` | Market, Filter, Sizing, BUY와 BLOCK Watch를 묶는 진입점 |
| `daily_feature_loader.py` | run date, data date와 market·stock feature 조회 |
| `daily_signal_builder.py` | sizing 결과를 Daily Signal 저장 형식으로 변환 |
| `daily_repository.py` | Daily Run과 Signal 생성·조회·상태 갱신 |
| `daily_block_watch_builder.py` | BLOCK 구간의 관찰 후보 선별 |
| `daily_block_watch_repository.py` | Block Watch 후보 저장과 대상 범위 정리 |

### 6.2 Daily Position 계열

| 파일 | 역할 |
|---|---|
| `daily_position_signal_run.py` | 활성 포지션 평가 진입점 |
| `daily_position_evaluator.py` | Position Decision v1 |
| `daily_position_evaluator_v2.py` | Daily 검증과 common sell 재사용 기반 v2 |
| `daily_position_repository.py` | 포지션·snapshot·feature 조회와 Decision 저장 |

### 6.3 공통 판단 Adapter

| 파일 | 역할 |
|---|---|
| `backtest_market.py` | Common Market 판단을 Decision 형식으로 변환 |
| `backtest_filter.py` | Common Buy Filter 호출 Adapter |
| `backtest_sizing.py` | Common Position Allocation 호출 Adapter |
| `backtest_decision_run.py` | 단일 일자 Decision Snapshot 보조 진입점 |

전체 파일의 입출력, DB 접근과 변경 영향은 `docs/source-file-catalog.md`에서 관리한다. 작은 helper나 로컬 dump는 운영 책임이 확인되기 전까지 주요 구조로 단정하지 않는다.

## 7. `port_strategy_common` 의존성

Decision의 핵심 판단 로직 상당 부분은 `port_strategy_common`을 재사용한다.

| 영역 | 주요 계약 |
|---|---|
| Config | Strategy Name, Engine Version, Market·Filter·Sizing 설정과 Snapshot |
| Market | Market Context와 Market Decision |
| Buy Filter | Buy Candidate Filter |
| Sizing | Position Allocation |
| Guard | Buy Guard와 Size Haircut |
| BLOCK Watch | Block Watch Candidate 평가 |
| Sell | Common Backtest Sell Decision |

현재 문서에서 확인되는 주요 사용 관계는 다음과 같다.

| 파일 | Common 사용 |
|---|---|
| `backtest_market.py` | `common_decide_market` |
| `backtest_filter.py` | `common_filter_buy_candidates` |
| `backtest_sizing.py` | `common_allocate_positions` |
| `daily_buy_signal_run.py` | Buy Guard, Size Haircut, Safe Float |
| `daily_block_watch_builder.py` | Block Watch Candidate 평가 |
| `daily_position_evaluator_v2.py` | `common_evaluate_backtest_sell` |

Public 함수명, dataclass 필드, enum, config key와 reason 문자열은 다른 서비스와 연결될 수 있다. Decision 단독 판단으로 변경하지 않는다.

## 8. AWS Paper Daily 위치

Decision은 AWS Paper Daily에서 판단 단계로 사용된다. Scheduler, Step Functions state와 Lambda 세부 구현은 각 담당 저장소가 관리한다.

| Daily 단계 | Decision 역할 |
|---|---|
| Step 6 · Daily Buy Signal | total feature를 읽어 Market, Filter, Sizing, BUY 또는 BLOCK Watch 결과 저장 |
| Step 7 · Position Signal | 활성 포지션을 읽어 HOLD, SELL, SKIP Decision 저장 |

### 8.1 Step 6

| 항목 | 값 |
|---|---|
| 진입점 | `daily_buy_signal_run.py` |
| 입력 | Market·Stock Total Feature, Universe와 판단 설정 |
| 출력 | Daily Run, Daily Signal 또는 Block Watch Candidate |
| 직접 하지 않는 일 | Execution Plan 생성, 주문 요청과 broker 주문 제출 |

### 8.2 Step 7

| 항목 | 값 |
|---|---|
| 진입점 | `daily_position_signal_run.py` |
| 입력 | Latest Completed Run, Active Position, Broker Snapshot, Feature |
| 출력 | Position Decision과 Position State 최신 평가 |
| 직접 하지 않는 일 | 매도 주문 요청 생성과 broker 주문 제출 |

실제 cluster, task definition ARN, image URI, subnet, security group, command id와 credential은 README에 기록하지 않는다.

## 9. 컨테이너 이미지

`Dockerfile`은 Decision 실행 이미지를 정의한다.

| 항목 | 현재 문서 기준 |
|---|---|
| Base Image | Python 3.13 slim |
| 기본 CMD | `python -m port_strategy_decision.daily_buy_signal_run` |
| Position 실행 | 컨테이너 command override로 `daily_position_signal_run` 지정 |
| Common 포함 | `port_strategy_common` vendoring |
| 배포 책임 | 별도 배포 파이프라인 |

Common vendoring은 현재 운영 연결을 위한 방식이다. 정식 패키징과 버저닝이 도입되면 교체 여부를 다시 판단한다.

## 10. 실행 방법

내부 import가 `from port_strategy_decision.xxx import ...` 형식이므로 파일 경로 직접 실행보다 `python -m` 형식을 사용한다.

아래 명령은 실행 형식을 설명하기 위한 예시다. DB 조회와 쓰기가 발생할 수 있으므로 문서 작업 중에는 실행하지 않는다.

```powershell
python -m port_strategy_decision.daily_buy_signal_run `
  --run-date 2026-05-26 `
  --data-date 2026-05-25

python -m port_strategy_decision.daily_position_signal_run `
  --evaluator-version v2

python -m port_strategy_decision.daily_position_signal_run `
  --validate-only

python -m port_strategy_decision.daily_validator
```

| 진입점 | 실행 영향 |
|---|---|
| `daily_buy_signal_run` | Daily Run, Signal과 Block Watch 데이터 생성·갱신 가능 |
| `daily_position_signal_run` | Position Decision과 Position State 갱신 가능 |
| `daily_validator` | DB 조회와 데이터 출력 가능 |
| `backtest_decision_run` | Run 기록은 만들지 않더라도 DB feature 조회 가능 |

## 11. 설정

설정은 `port_strategy_common.config`와 로컬 `db_config.py`를 사용한다.

### 11.1 주요 설정 영역

| 설정 | 용도 |
|---|---|
| PostgreSQL 연결 | host, port, database, user와 password |
| Strategy 설정 | Strategy Name과 Engine Version |
| Market 설정 | 시장 상태와 노출 한도 판단 |
| Filter 설정 | 매수 후보 기준 |
| Sizing 설정 | 후보별 비중과 수량 계산 |
| Decision Run Date | 실행 기준일 override 후보 |
| Schema 계약 | Feature 입력과 Strategy 출력 테이블 해석 |

### 11.2 DB 환경변수

현재 문서와 `db_config.py` 계약은 `INTEREST_DB_*` 계열을 기준으로 한다.

```powershell
$env:INTEREST_DB_HOST="localhost"
$env:INTEREST_DB_PORT="5433"
$env:INTEREST_DB_NAME="portfolio"
$env:INTEREST_DB_USER="postgres"
$env:INTEREST_DB_PASSWORD="[REDACTED]"
```

| 환경변수 | 현재 문서 기준 |
|---|---|
| `INTEREST_DB_HOST` | 기본 `localhost` |
| `INTEREST_DB_PORT` | 기본 `5433` |
| `INTEREST_DB_NAME` | 기본 `portfolio` |
| `INTEREST_DB_USER` | 기본 `postgres` |
| `INTEREST_DB_PASSWORD` | 기본값 없음, 누락 시 실행 오류 |

실제 credential은 환경변수나 local secret loader로 관리한다. password, token, account, webhook URL은 문서와 로그에 원문으로 남기지 않는다.

### 11.3 Search Path

현재 문서 기준 DB connection의 search path는 아래 순서를 사용한다.

```text
decision, research, preprocessor, execution, connector, reference, legacy, public
```

| Schema | 주요 역할 |
|---|---|
| `decision` | Daily Run, Signal과 Position Decision |
| `research` | Block Watch Candidate |
| `preprocessor` | Market·Stock Total Feature |
| `execution` | 후속 실행 계약 참조 |
| `connector` | Balance와 Position Snapshot |
| `reference` | Stock Universe 등 기준 정보 |
| `legacy`, `public` | 기존 unqualified SQL 호환 |

`strategy_block_watch_candidate` 사용 때문에 `research` schema가 search path에 포함된다. 순서 변경은 unqualified SQL의 대상 table을 바꿀 수 있으므로 계약 변경으로 취급한다.

## 12. 외부 의존성

| 의존성 | 용도 |
|---|---|
| Python | Runtime |
| PostgreSQL | Feature 조회와 Decision 저장 |
| `psycopg2` | PostgreSQL 연결 |
| `psycopg2.extras` | Row와 Batch 처리 보조 |
| `port_strategy_common` | Market, Filter, Sizing, Guard와 Sell 공통 판단 |
| Preprocessor Feature | Decision 입력 |
| Connector Snapshot | Position 평가 입력 |
| StrategyExecution | Daily Signal 후속 소비자 |

Dependency의 정확한 설치 버전과 배포 구성은 `requirements.txt`, Dockerfile과 배포 저장소를 함께 확인한다.

## 13. 상태와 재실행 주의사항

| 주의사항 | 확인 내용 |
|---|---|
| 부분 성공 | 일부 row 저장 후 Run만 성공 처리되지 않는지 확인 |
| 재실행 | 동일 run date와 data date의 중복·잔존 row 확인 |
| Transaction | delete, insert, upsert와 상태 갱신의 commit 경계 확인 |
| Feature 누락 | 누락값을 실제 0값으로 오인하지 않는지 확인 |
| Position 정합 | Strategy Position과 Broker Position의 ticker·수량 비교 |
| 상태 문자열 | BUY, BLOCK, HOLD, SELL, SKIP과 reason 의미 유지 |
| 버전 | Evaluator Version과 Engine Version 보존 |

현재 구현이 모든 부분 실패를 자동 차단한다고 README만으로 단정하지 않는다. 실제 변경이나 장애 분석에서는 entrypoint와 repository의 예외 전파, commit과 최종 상태 처리까지 확인해야 한다.

## 14. 문서 구조

| 문서 | 역할 |
|---|---|
| `AGENTS.md` | Kiro 작업 범위, 안전, 데이터 계약과 검증 규칙 |
| `README.md` | 현재 서비스 구조, 흐름, 실행·설정과 운영 위치 |
| `CHANGELOG.md` | 주요 변경 이력과 당시 사실 |
| `docs/source-file-catalog.md` | 운영상 중요한 파일의 역할, 입출력과 변경 영향 |

파일 책임, entrypoint, DB 접근, Common 의존성 또는 운영 wrapper가 바뀌면 README와 `docs/source-file-catalog.md`를 함께 확인한다. 날짜별 worklog 문서는 새로 만들지 않는다.

## 15. 안전한 검증 범위

문서만 수정한 경우에는 변경 파일과 diff 범위만 확인한다.

```powershell
git status --short
git diff --stat
```

코드 변경 시에도 실제 Daily Signal, Position Signal, backtest, DB 쓰기, 외부 API, AWS와 주문 실행이 없는 검증을 우선한다. 운영 실행이 필요한 검증은 자동 수행하지 않고 남은 검증으로 보고한다.

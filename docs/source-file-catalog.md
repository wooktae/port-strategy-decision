# Source File Catalog

`port_strategy_decision`의 주요 파일 책임, 입력·출력, 변경 영향과 실행 위험을 정리한다.

이 문서는 전체 repository inventory가 아니다. Decision 흐름을 이해하고 유지보수하는 데 필요한 파일만 관리한다.

## 1. 문서 목적

| 항목 | 값 |
|---|---|
| 대상 | `port_strategy_decision` 루트와 `docs/source-file-catalog.md` |
| 기준 | 현재 문서화된 파일 구조, import, entrypoint와 데이터 계약 |
| 제외 | build 결과물, cache, IDE 파일, `__pycache__`, 일회성 dump |
| 주요 관점 | 파일 책임, 입력, 출력, DB 영향, 실행 위험, 변경 연동 |
| 실제 실행 | 문서 정리 과정에서 수행하지 않음 |
| 미확인 사항 | 실제 코드 최종 대조가 필요한 내용은 추정하지 않음 |

## 2. 서비스 흐름

| 단계 | 책임 |
|---|---|
| Feature Load | total market·stock feature와 universe를 조회 |
| Market Decision | 시장 상태와 허용 노출 범위를 판단 |
| Buy Filter | 매수 후보를 선별 |
| Sizing | 후보별 배분 수량과 비중을 계산 |
| BUY Signal | 실행 계층이 소비할 READY signal을 저장 |
| BLOCK Watch | BUY를 만들지 않고 관찰 후보만 저장 |
| Position Decision | 활성 포지션을 HOLD·SELL·SKIP으로 평가 |
| State Update | position decision과 최신 평가 상태를 저장 |

## 3. Root와 공통 파일

| 파일 | 역할 |
|---|---|
| `__init__.py` | `port_strategy_decision` 패키지 import 기준점 |
| `db_config.py` | `INTEREST_DB_*` 환경변수와 Decision DB 연결 설정 관리 |
| `requirements.txt` | 컨테이너에서 설치할 Python dependency 목록 |
| `Dockerfile` | Daily Decision 컨테이너 이미지와 기본 CMD 정의 |
| `.dockerignore` | 이미지 build 컨텍스트 제외 규칙 |
| `pytest.ini` | pytest 설정 |
| `.github/workflows/` | GitHub Actions → CodeBuild 트리거 |
| `.devops/` | CI buildspec과 smoke script |
| `tests/` | import·evaluator version contract 테스트 |

### 3.1 `__init__.py`

| 항목 | 값 |
|---|---|
| 책임 | 패키지 초기화 |
| 기능 로직 | 없음 |
| 변경 영향 | `python -m port_strategy_decision.<module>` import 구조 |
| 주의 | 기능이 없어 보여도 임의 삭제하지 않음 |

### 3.2 `db_config.py`

| 항목 | 값 |
|---|---|
| 책임 | PostgreSQL 접속 설정 중앙화 |
| 주요 입력 | `INTEREST_DB_HOST`, `PORT`, `NAME`, `USER`, `PASSWORD` |
| Password | 기본값 없이 외부에서 주입 |
| Search path | Decision과 연계 domain schema 탐색 순서 설정 |
| 호출 영향 | 연결 생성 시 DB 접속 발생 가능 |
| 변경 위험 | 기본 DB, schema 순서와 credential 처리 계약 |
| 주의 | 실제 접속값을 문서·로그에 기록하지 않음 |

### 3.3 `requirements.txt`

| 항목 | 값 |
|---|---|
| 현재 명시 dependency | `psycopg2-binary` |
| Common 처리 | `port_strategy_common`은 requirements가 아니라 Docker build 시 1.0.0 Wheel로 설치 |
| 변경 영향 | 이미지 build와 runtime import |
| 주의 | 실제 import 확인 없이 dependency를 임의 추가·삭제하지 않음 |

### 3.4 `Dockerfile`

| 항목 | 값 |
|---|---|
| 기반 이미지 | Python 3.13 slim |
| 포함 대상 | `port_strategy_common`, `port_strategy_decision` |
| Common 설치 | `.devops/packages`의 1.0.0 Wheel을 `--no-deps` 설치 |
| 기본 CMD | `python -m port_strategy_decision.daily_buy_signal_run` |
| 다른 진입점 | 실행 시 command override 사용 가능 |
| 운영 위치 | ECS RunTask 또는 동일 컨테이너 실행 대상 |
| 저장소 경계 | ECR push와 task definition 등록은 배포 영역 |
| 주의 | 실제 URI, ARN, subnet, security group을 문서에 기록하지 않음 |

### 3.5 CI·배포 구성

| 파일 | 역할 |
|---|---|
| `.github/workflows/decision-codebuild.yml` | `workflow_dispatch`로 CodeBuild 시작·상태 대기 |
| `.devops/codebuild/buildspec.yml` | 품질 게이트, Common Wheel download, Docker build, 선택적 ECR push |
| `.devops/scripts/container-smoke.py` | import-only smoke, DB 연결·run 함수 미호출 |
| `.devops/scripts/entrypoint-smoke.py` | argparse `--help` 경로만 실행하는 entrypoint smoke |
| `.dockerignore` | 이미지 build 컨텍스트 제외 규칙 |

| 항목 | 값 |
|---|---|
| 인증 | GitHub OIDC |
| Common Wheel | CodeArtifact 1.0.0 Wheel을 `.devops/packages`에 준비 |
| Wheel 추적 | `.devops/packages/*.whl`은 git-ignore된 빌드 산출물 |
| ECR push | `PUSH_IMAGE=true`에서만 수행 |
| 실행 위험 | buildspec은 AWS·Docker 호출 포함, 문서 작업 중 실행하지 않음 |
| 민감정보 | Account ID, ARN, 전체 Digest, CodeArtifact 전체 식별자 미기록 |

### 3.6 테스트

| 파일 | 역할 |
|---|---|
| `pytest.ini` | pytest 설정 |
| `tests/conftest.py` | flat 레이아웃용 `port_strategy_decision` 패키지 등록 |
| `tests/test_import_contract.py` | Decision·Common 모듈 import 계약 (DB·run 미호출) |
| `tests/test_position_version_contract.py` | Evaluator version 기본 v1, 지원 {v1,v2} 계약 |

| 항목 | 값 |
|---|---|
| 성격 | side effect 없는 정적 계약 검증 |
| 실행 위험 | DB·주문·AWS 미접근 |
| 연동 | buildspec Unit·Contract Test 단계 |

## 4. Daily Buy Signal

Daily Buy 흐름은 feature를 읽고 market, filter와 sizing을 수행한 뒤 BUY signal 또는 BLOCK watch를 저장한다.

| 순서 | 파일 |
|---|---|
| 1 | `daily_buy_signal_run.py` |
| 2 | `daily_feature_loader.py` |
| 3 | `backtest_market.py` |
| 4 | `backtest_filter.py` |
| 5 | `backtest_sizing.py` |
| 6 | `daily_signal_builder.py` |
| 7 | `daily_repository.py` |
| 분기 | `daily_block_watch_builder.py`, `daily_block_watch_repository.py` |

### 4.1 `daily_buy_signal_run.py`

| 항목 | 값 |
|---|---|
| 책임 | Daily BUY 전체 흐름 orchestration |
| 주요 입력 | Run date, data date, total feature와 strategy config |
| 주요 처리 | Feature load, market, filter, sizing과 저장 |
| 정상 시장 출력 | Daily run과 BUY signal |
| BLOCK 시장 출력 | BUY signal 없이 watch candidate |
| 상태 처리 | Daily run lifecycle 갱신 |
| DB 영향 | 조회와 쓰기 |
| 후속 영향 | StrategyExecution이 소비할 signal 생성 가능 |
| 실행 모드 | 운영 모드와 read-only `--shadow` 모드 (write_count=0, JSON) |
| 실행 위험 | 운영 모드는 실제 운영 데이터 변경 |
| 주의 | 문서화·정적 분석 중 실행하지 않음 |

### 4.2 `daily_feature_loader.py`

| 항목 | 값 |
|---|---|
| 책임 | Daily 판단 입력 조회 |
| 날짜 책임 | Run date와 data date 결정 |
| Market 입력 | `pre_total_market_daily_feature` |
| Stock 입력 | `pre_total_stock_daily_feature` |
| Universe 입력 | `stock_universe` |
| DB 영향 | 조회 |
| 변경 위험 | 날짜 기준, table, filter와 row shape |
| 연동 파일 | `daily_buy_signal_run.py`, `backtest_market.py`, `backtest_filter.py` |
| 주의 | 누락 feature와 빈 결과를 정상값으로 임의 변환하지 않음 |

### 4.3 `daily_signal_builder.py`

| 항목 | 값 |
|---|---|
| 책임 | Sizing 결과를 저장 가능한 BUY signal row로 변환 |
| 주요 입력 | Sizing 결과와 stock feature |
| 주요 출력 | `strategy_daily_signal` 저장 형식 |
| 고정 의미 | `signal_type=BUY` |
| 초기 상태 | `signal_status=READY` |
| 주요 payload | Feature snapshot, buy info, raw feature와 entry reason |
| DB 직접 쓰기 | 없음 |
| 변경 위험 | 필드명, 상태값, reason과 source table 의미 |
| 주의 | Builder 출력은 StrategyExecution 계약과 연결됨 |

### 4.4 `daily_repository.py`

| 항목 | 값 |
|---|---|
| 책임 | Daily run과 BUY signal persistence |
| 주요 table | `strategy_daily_run`, `strategy_daily_signal` |
| 주요 처리 | 생성, 조회, 상태 갱신과 signal upsert |
| DB 영향 | 읽기와 쓰기 |
| 재실행 위험 | 동일 기준일 중복 또는 기존 row 갱신 |
| 변경 위험 | Unique key, run status, signal status와 upsert |
| 연동 파일 | `daily_buy_signal_run.py`, `daily_signal_builder.py` |
| 주의 | 부분 저장 후 성공 처리되지 않도록 transaction 경계를 확인 |

## 5. BLOCK Watch

BLOCK Watch는 시장이 BLOCK일 때 BUY signal을 만들지 않고 강한 예외 후보만 관찰용으로 남기는 보조 흐름이다.

### 5.1 `daily_block_watch_builder.py`

| 항목 | 값 |
|---|---|
| 책임 | BLOCK 후보 평가 결과를 저장 row로 변환 |
| 공통 로직 | `evaluate_block_watch_candidate` |
| 주요 입력 | Stock feature와 BLOCK 구간 후보 정보 |
| 주요 출력 | `strategy_block_watch_candidate` 저장 형식 |
| BUY 생성 | 하지 않음 |
| 주문 생성 | 하지 않음 |
| DB 직접 쓰기 | 없음 |
| 변경 위험 | 후보 기준, reason과 payload 계약 |
| 주의 | BUY 우회 경로로 바꾸지 않음 |

### 5.2 `daily_block_watch_repository.py`

| 항목 | 값 |
|---|---|
| 책임 | BLOCK watch candidate 저장과 정리 |
| 주요 table | `strategy_block_watch_candidate` |
| 주요 처리 | Upsert와 daily run 단위 삭제 |
| DB 영향 | 쓰기와 삭제 |
| 재실행 위험 | 기존 후보 삭제 후 재생성 범위 |
| 변경 위험 | Unique key, delete 조건과 transaction |
| 연동 파일 | `daily_buy_signal_run.py`, `daily_block_watch_builder.py` |
| 주의 | 다른 run이나 기준일 후보를 삭제하지 않도록 범위 확인 |

## 6. Market·Filter·Sizing Adapter

이 파일들은 `port_strategy_common`의 판단 로직을 Decision 계층의 row와 객체 계약에 연결한다.

### 6.1 `backtest_market.py`

| 항목 | 값 |
|---|---|
| 책임 | Market feature를 Common market context로 변환 |
| 공통 함수 | `common_decide_market` |
| 주요 입력 | Total market feature row |
| 주요 출력 | Decision 계층 `MarketDecision` |
| DB 직접 접근 | 없음 |
| 변경 위험 | Context field, config와 `MarketDecision` mapping |
| 재사용 | Daily Buy와 decision snapshot |
| 주의 | Common 함수 결과 의미를 Decision에서 재해석하지 않음 |

### 6.2 `backtest_filter.py`

| 항목 | 값 |
|---|---|
| 책임 | Stock feature 후보를 Common buy filter에 연결 |
| 공통 함수 | `common_filter_buy_candidates` |
| 주요 입력 | Stock feature 목록과 market decision |
| 주요 출력 | 통과·제외 후보와 reason |
| DB 직접 접근 | 없음 |
| 변경 위험 | Candidate row field, filter config와 reason |
| 재사용 | Daily Buy와 decision snapshot |
| 주의 | 필터 탈락을 데이터 누락과 혼동하지 않음 |

### 6.3 `backtest_sizing.py`

| 항목 | 값 |
|---|---|
| 책임 | 필터 통과 후보의 position allocation 계산 연결 |
| 공통 함수 | `common_allocate_positions` |
| 주요 입력 | Buy candidate와 market decision |
| 주요 출력 | 후보별 sizing 결과 |
| DB 직접 접근 | 없음 |
| 변경 위험 | 수량·비중 의미와 `SIZING_CONFIG` |
| 재사용 | Daily Buy와 decision snapshot |
| 주의 | 반올림, 최소 주문과 exposure 의미를 임의 변경하지 않음 |

## 7. Decision Snapshot 후보

### 7.1 `backtest_decision_run.py`

| 항목 | 값 |
|---|---|
| 책임 | 단일 일자 market·filter·sizing snapshot 출력 |
| 주요 입력 | DB의 market·stock feature |
| 사용 adapter | `backtest_market.py`, `backtest_filter.py`, `backtest_sizing.py` |
| Run store | Common run store를 사용하지 않음 |
| Run id 생성 | 하지 않음 |
| DB 영향 | Feature 조회 |
| 출력 | 판단 snapshot 콘솔 출력 |
| 분류 | Backtest 성격의 실행 후보 |
| 실행 위험 | 운영 DB 조회와 데이터 출력 |
| 주의 | 문서화 작업과 backtest 금지 범위에서는 실행하지 않음 |

## 8. Daily Position Decision

Position 흐름은 최신 완료 daily run, 활성 포지션, broker snapshot과 feature를 결합해 HOLD, SELL 또는 SKIP 판단을 저장한다.

| 순서 | 파일 |
|---|---|
| 1 | `daily_position_signal_run.py` |
| 2 | `daily_position_repository.py` |
| 3 | `daily_position_evaluator.py` 또는 `daily_position_evaluator_v2.py` |
| 4 | `daily_position_repository.py` |

### 8.1 `daily_position_signal_run.py`

| 항목 | 값 |
|---|---|
| 책임 | Position 조회, 평가, 저장과 요약 orchestration |
| 주요 입력 | 최신 완료 run, active position, broker snapshot과 feature |
| Evaluator | v1 또는 v2, 운영 기본 v1 |
| 실행 모드 | 운영 모드와 read-only `--shadow` 모드 (write_count=0, JSON) |
| 주요 출력 | HOLD, SELL, SKIP decision |
| DB 영향 | 조회와 쓰기 |
| 상태 영향 | `strategy_position_state` 최신 평가 갱신 |
| 후속 영향 | StrategyExecution의 매도 판단 입력 가능 |
| 실행 위험 | 운영 모드는 position decision 변경 |
| 주의 | 문서화·정적 분석 중 실행하지 않음 |

### 8.2 `daily_position_evaluator.py`

| 항목 | 값 |
|---|---|
| 책임 | Daily Position v1 판단 |
| 주요 기준 | Hard stop, 최소·최대 보유일과 market BLOCK |
| 추가 기준 | 품질 저하와 수익권 HOLD |
| 주요 출력 | HOLD, SELL 또는 SKIP 저장 dict |
| DB 직접 접근 | 없음 |
| DB 직접 쓰기 | 없음 |
| 변경 위험 | 기준 우선순위, 상태값과 reason |
| 주의 | 기존 운영 SELL v1 의미와 호환 유지 |

### 8.3 `daily_position_evaluator_v2.py`

| 항목 | 값 |
|---|---|
| 책임 | Daily 검증과 Common sell 판단 결합 |
| 선행 처리 | Daily 운영용 필수 검증 |
| 공통 함수 | `common_evaluate_backtest_sell` |
| 주요 출력 | Common 결과를 Daily decision 형식으로 mapping |
| DB 직접 접근 | 없음 |
| 변경 위험 | 선행 검증 순서, mapping, status와 reason |
| 주의 | Common 결과를 누락하거나 다른 의미로 변환하지 않음 |

### 8.4 `daily_position_repository.py`

| 항목 | 값 |
|---|---|
| 책임 | Position 판단에 필요한 조회와 결과 저장 |
| 주요 조회 | Active position, broker snapshot, stock·market feature |
| 주요 저장 | `strategy_daily_position_decision` |
| 상태 갱신 | `strategy_position_state` latest 평가 |
| DB 영향 | 읽기와 쓰기 |
| 재실행 위험 | 동일 position·기준일 decision 중복 또는 갱신 |
| 변경 위험 | Join 기준, unique key, upsert와 latest 갱신 |
| 주의 | Broker snapshot 누락과 실제 0 position을 구분 |

## 9. 검증·조회 도구

### 9.1 `daily_validator.py`

| 항목 | 값 |
|---|---|
| 책임 | 최신 daily run과 연결 signal 조회 |
| DB 영향 | 조회 |
| 출력 | 운영 데이터 콘솔 출력 |
| 검증 성격 | 사람이 저장 결과를 확인하는 보조 도구 |
| 변경 위험 | 조회 기준과 출력 범위 |
| 보안 위험 | 계좌·종목·운영 데이터 노출 가능성 |
| 실행 조건 | 출력 필드와 대상 환경을 먼저 확인 |
| 주의 | 안전한 정적 분석 도구로 간주하지 않음 |

## 10. 데이터 계약

### 10.1 주요 입력

| 데이터 | 역할 |
|---|---|
| `pre_total_market_daily_feature` | Market decision 입력 |
| `pre_total_stock_daily_feature` | Buy filter, sizing과 position 평가 입력 |
| `stock_universe` | 종목명(company_name) 보강용 LEFT JOIN 대상 |
| Active position | 보유 포지션 평가 대상 |
| `connector_balance_snapshot` | Position 평가에서 최신 broker snapshot 기준일 확인 |
| `connector_position_snapshot` | Broker 보유 수량과 상태 확인 |

### 10.2 주요 출력

| 데이터 | 역할 |
|---|---|
| `strategy_daily_run` | Daily Buy 실행 단위와 lifecycle |
| `strategy_daily_signal` | READY BUY 판단 |
| `strategy_block_watch_candidate` | BLOCK 구간 관찰 후보 |
| `strategy_daily_position_decision` | HOLD·SELL·SKIP 판단 이력 |
| `strategy_position_state` | 포지션별 최신 전략 평가 상태 |

### 10.3 변경 시 확인할 계약

| 항목 | 확인 내용 |
|---|---|
| Table | Schema, table name과 search path |
| Column | Type, NULL 허용과 의미 |
| Key | Unique key와 group key |
| Date | Run date, data date와 기준일 |
| Status | Run, signal과 position 상태값 |
| Reason | Common과 downstream이 소비하는 문자열 |
| Payload | Feature snapshot과 JSON shape |
| Transaction | 부분 성공과 rollback 범위 |
| Re-run | 중복, delete와 upsert 동작 |

## 11. 실행 위험 분류

| 등급 | 의미 |
|---|---|
| 읽기 | DB 조회와 운영 데이터 출력 가능 |
| 쓰기 | Strategy table insert·update·upsert 가능 |
| 삭제 | 특정 run 또는 기준일 row 삭제 가능 |
| 후속 영향 | Execution 계층이 소비할 산출물 생성 가능 |

### 11.1 파일별 위험

| 파일 | 위험 |
|---|---|
| `daily_buy_signal_run.py` | 조회, 쓰기와 후속 BUY 흐름 영향 |
| `daily_repository.py` | Daily run·signal 쓰기 |
| `daily_block_watch_repository.py` | Watch candidate 쓰기·삭제 |
| `daily_position_signal_run.py` | 조회, decision 저장과 state 갱신 |
| `daily_position_repository.py` | Position decision 쓰기와 state 갱신 |
| `backtest_decision_run.py` | DB 조회와 snapshot 출력 |
| `daily_validator.py` | DB 조회와 운영 데이터 출력 |
| `daily_feature_loader.py` | DB feature 조회 |
| Builder·Evaluator·Adapter | 직접 DB 쓰기는 없지만 저장 계약에 영향 |

### 11.2 문서 작업 중 실행하지 않는 대상

| 대상 | 이유 |
|---|---|
| Daily Buy entrypoint | Strategy run과 BUY signal 변경 가능 |
| Position entrypoint | Position decision과 state 변경 가능 |
| Repository 함수 | DB 쓰기·삭제 가능 |
| Backtest snapshot | 운영 DB 조회 발생 |
| Validator | 운영 데이터 출력 가능 |
| Container default CMD | Daily Buy entrypoint 실행 |
| AWS RunTask | 실제 운영 실행으로 연결 |

## 12. `port_strategy_common` 연동

| 영역 | 연동 |
|---|---|
| Config | Strategy name, engine version과 판단 config |
| Market | `common_decide_market` |
| Buy Filter | `common_filter_buy_candidates` |
| Sizing | `common_allocate_positions` |
| Guard | Buy guard와 size haircut 계열 |
| BLOCK Watch | `evaluate_block_watch_candidate` |
| Sell | `common_evaluate_backtest_sell` |

### 변경 주의

| 항목 | 원칙 |
|---|---|
| Public 함수 | 명시 요청 없이 이름·signature 변경 금지 |
| Dataclass | 필드명과 타입 계약 유지 |
| Enum·상태값 | Downstream 호환 확인 |
| Reason 문자열 | 저장 데이터와 화면·실행 계층 영향 확인 |
| Config | Default와 snapshot 호환 확인 |
| Wheel 설치 | 1.0.0 Wheel 설치 방식과 Dockerfile·buildspec 일치 유지 |

## 13. AWS와 운영 위치

| 항목 | 값 |
|---|---|
| Paper Daily Step 6 | `daily_buy_signal_run.py` |
| Paper Daily Step 7 | `daily_position_signal_run.py` |
| Orchestration | Scheduler와 Step Functions 책임 |
| 실행 방식 | ECS RunTask 또는 동일 컨테이너 |
| 기본 이미지 CMD | Daily Buy Signal |
| Position 실행 | Command override 필요 |
| 저장소 증거 | Dockerfile, Python entrypoint와 `.devops`·`.github` CI 구성 |
| 외부 운영 사실 | Cluster, task definition과 Scheduler 문서에서 관리 |

Repository 파일로 확인되는 구조와 실제 AWS 현재 상태를 혼동하지 않는다.

## 14. 문서 파일

| 파일 | 역할 |
|---|---|
| `AGENTS.md` | 작업 범위, 안전, 데이터 계약과 완료 기준 |
| `README.md` | 서비스 구조, 흐름, 설정과 운영 AS-IS |
| `CHANGELOG.md` | 기능·문서 기준 변경 이력 |
| `docs/source-file-catalog.md` | 파일 책임, 입출력과 변경 영향 |

### 문서별 갱신 기준

| 문서 | 갱신 조건 |
|---|---|
| `AGENTS.md` | 작업 규칙, 안전 기준과 필수 계약이 바뀜 |
| `README.md` | 서비스 책임, 흐름, 설정, entrypoint와 운영 위치가 바뀜 |
| `CHANGELOG.md` | 실제 기능, 구조 또는 문서 기준이 바뀜 |
| `docs/source-file-catalog.md` | 파일 추가·삭제·이동, 책임, 입출력과 실행 위험이 바뀜 |

날짜별 `docs/worklog/*.md`는 새로 만들지 않는다. 과거 생성 사실은 CHANGELOG의 당시 이력으로만 보존한다.

## 15. 정리 후보

| 파일 | 현재 판단 |
|---|---|
| `backtest_decision_run.py` | DB 조회가 있는 snapshot 도구로 유지 |
| `daily_validator.py` | 운영 조회·출력 도구로 유지 |
| 기타 tracked source | 현재 삭제 확정 대상 없음 |

다음 조건을 충족하기 전에는 파일을 삭제하지 않는다.

| 확인 | 기준 |
|---|---|
| Import | 다른 파일에서 참조하지 않음 |
| Entrypoint | Local, Docker와 AWS command에서 호출하지 않음 |
| DB 계약 | 운영 검증이나 수동 복구에 사용되지 않음 |
| 문서 | README, CHANGELOG와 catalog에서 책임 정리 |
| 승인 | 사용자의 명시적 삭제 요청 |

## 16. 카탈로그 갱신 조건

다음 변경이 발생하면 이 문서를 같은 작업에서 갱신한다.

| 변경 | 반영 내용 |
|---|---|
| 파일 추가 | 역할, 입력, 출력과 위험 추가 |
| 파일 삭제 | 참조 제거와 삭제 이력 확인 |
| 파일 이동 | 경로와 import·entrypoint 영향 수정 |
| Entrypoint 변경 | Daily Step과 Docker CMD 반영 |
| Table 변경 | 입력·출력 계약과 repository 책임 수정 |
| Status 변경 | Builder, repository와 downstream 영향 수정 |
| Common 변경 | Adapter mapping과 public 계약 수정 |
| Docker 변경 | Runtime, Common Wheel 설치와 command 수정 |
| CI·배포 구성 변경 | Workflow, buildspec과 smoke script 반영 |
| 실행 위험 변경 | 읽기·쓰기·삭제·후속 영향 재분류 |
| 문서 체계 변경 | AGENTS, README와 CHANGELOG 역할 정합성 수정 |

카탈로그에는 확인된 현재 책임만 기록한다. 존재하지 않는 파일, 추정한 AWS 리소스와 미확인 동작은 추가하지 않는다.

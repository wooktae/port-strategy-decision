# AGENTS.md - port_strategy_decision

## 0. 최우선 문서 가독성 규칙

모든 작업은 정확성과 함께 읽기 쉬운 결과를 우선한다.

| 항목 | 규칙 |
|---|---|
| 기본 표 | 새로 만드는 독립 요약 표는 기본 2컬럼으로 작성한다. |
| 권장 컬럼 | `항목 / 값`, `파일 / 역할`, `계층 / 책임`, `상태 / 의미`를 우선한다. |
| 기존 표 | 기존 표에 행을 추가할 때는 기존 컬럼 구조를 유지한다. |
| 긴 셀 | 한 셀에는 핵심 사실 1~2개만 넣고, 3개 이상이면 여러 행이나 상세 문서로 분리한다. |
| 길이 제한 | 표 셀 300자, 일반 Markdown 한 줄 500자를 넘기지 않는다. |
| 반복 금지 | 같은 설명을 README, CHANGELOG, source catalog에 장문으로 반복하지 않는다. |
| 상태 표현 | 현재 구현, 설계 원칙, 운영 사실, 미검증 추정을 명확히 구분한다. |
| 원문 출력 | raw log, 전체 SQL, 전체 DB 결과, 민감정보 원문을 문서에 넣지 않는다. |
| 인코딩 | 한글 Markdown은 UTF-8 No BOM으로 저장한다. |

문서 역할은 아래처럼 분리한다.

| 문서 | 역할 |
|---|---|
| `AGENTS.md` | Kiro가 작업할 때 지켜야 할 범위, 안전, 데이터 계약과 검증 규칙 |
| `README.md` | 현재 구조, 책임 경계, 실행·설정 방법과 AS-IS 운영 이해 |
| `CHANGELOG.md` | 실제 변경 이력과 당시 사실 보존 |
| `docs/source-file-catalog.md` | 운영과 유지보수에 중요한 파일 역할, 입출력과 변경 영향 |

## 1. 적용 범위와 우선순위

- 이 파일은 `port_strategy_decision` 전용 최우선 작업 규칙이다.
- 이 저장소 작업에서는 다른 마이크로서비스의 `AGENTS.md`를 작업 기준으로 사용하지 않는다.
- `.kiro/AGENTS.md`와 상충하면 이 파일의 Decision 전용 규칙을 우선한다.
- 현재 `port_strategy_decision` 루트와 하위 파일만 직접 수정한다.
- 루트 밖 파일은 계약 확인을 위한 read-only 참고만 허용한다.
- 사용자가 지정한 대상 파일이 있으면 그 파일만 수정한다.
- 전체 workspace 전수 스캔, sub-agent, orchestrator, 신규 scanner 생성은 금지한다.
- 변경은 작고 검증 가능한 범위로 유지한다.

## 2. 서비스 책임

이 저장소는 Preprocessor가 만든 total feature를 읽어 daily decision을 생성하는 계층이다.

| 계층 | Decision 책임 |
|---|---|
| Market | 시장 상태, 노출 한도, 최대 보유 수, 최소 점수·수급 기준 판단 |
| Buy Filter | 종목 feature를 매수 후보 기준에 맞게 필터링 |
| Sizing | 후보별 수량과 비중 계산 |
| Daily Buy | `strategy_daily_run`, `strategy_daily_signal` 생성과 상태 갱신 |
| BLOCK Watch | BUY 차단 구간에서 관찰 후보만 별도 기록 |
| Position | 활성 포지션을 HOLD, SELL, SKIP으로 평가 |
| Adapter | `port_strategy_common` 판단 결과를 daily 저장 형식으로 변환 |

Decision이 직접 담당하지 않는 범위는 아래와 같다.

| 영역 | 담당 계층 |
|---|---|
| 외부 데이터 수집 | Crawler |
| raw 데이터 전처리와 total feature 생성 | Preprocessor |
| execution plan과 주문 요청 구성 | StrategyExecution |
| broker 주문, 체결, 잔고와 보유 동기화 | MarketConnector |
| backtest 시나리오와 연구 보고서 | StrategyResearch |
| 화면 조회와 승인 UI | View |
| 전체 batch orchestration | Scheduler와 Step Functions |
| 이미지 build, ECR push, task definition 등록 | 배포 파이프라인 |

## 3. 핵심 실행 흐름

### 3.1 Daily Buy Signal

| 파일 | 역할 |
|---|---|
| `daily_buy_signal_run.py` | total feature를 읽어 market, filter, sizing, BUY와 BLOCK watch 흐름을 실행하는 진입점 |
| `daily_feature_loader.py` | run date, data date와 market·stock feature를 조회 |
| `backtest_market.py` | common market 판단 adapter |
| `backtest_filter.py` | common buy filter adapter |
| `backtest_sizing.py` | common sizing adapter |
| `daily_signal_builder.py` | sizing 결과를 daily signal 저장 형식으로 변환 |
| `daily_repository.py` | daily run과 signal 조회·저장·상태 갱신 |
| `daily_block_watch_builder.py` | BLOCK 구간의 관찰 후보 선별 |
| `daily_block_watch_repository.py` | block watch 후보 저장과 기존 범위 정리 |

### 3.2 Daily Position Signal

| 파일 | 역할 |
|---|---|
| `daily_position_signal_run.py` | 최신 완료 run과 활성 포지션을 읽어 HOLD, SELL, SKIP을 생성하는 진입점 |
| `daily_position_evaluator.py` | daily position v1 판단 |
| `daily_position_evaluator_v2.py` | daily 검증 후 common sell 판단을 재사용하는 v2 adapter |
| `daily_position_repository.py` | 포지션, broker snapshot, feature 조회와 decision 저장 |

### 3.3 조회와 보조 진입점

| 파일 | 취급 원칙 |
|---|---|
| `backtest_decision_run.py` | 단일 일자 decision snapshot 후보이며 DB 조회가 있으므로 문서 작업 중 실행하지 않는다. |
| `daily_validator.py` | DB 조회와 출력이 포함될 수 있으므로 구조 확인 후에만 실행 여부를 판단한다. |
| `decision_comparator.py` | 운영 DB read-only 조회와 Shadow JSON 비교 도구이므로 운영 중요 파일로 취급하고 문서 작업 중 실행하지 않는다. |
| `decision_comparison_ecs_run.py` | ECS Comparator wrapper이며 운영 BUY·Position entrypoint가 아니다. |
| test/debug/output 파일 | 운영 소스로 단정하지 않고 증거 확인 전에는 후보 또는 로컬 산출물로 표현한다. |

## 4. 입력 데이터 계약

Decision은 원천 데이터를 직접 만들지 않는다. 아래 입력을 읽어 판단을 수행한다.

| 입력 | 역할 |
|---|---|
| `pre_total_market_daily_feature` | market signal과 시장 단위 제한 판단 |
| `pre_total_stock_daily_feature` | 종목 필터, sizing과 position 평가 |
| `stock_universe` | 종목명(company_name) 보강용 LEFT JOIN 대상 |
| `connector_balance_snapshot` | Position 평가에서 최신 broker snapshot 기준일 확인 |
| `connector_position_snapshot` | broker 보유 상태 확인 |
| `strategy_position_state` | 전략 포지션의 최신 평가 상태 |

입력 관련 규칙:

- run date와 data date를 혼용하지 않는다.
- 동일 실행에서 market과 stock feature의 기준일 정합을 확인한다.
- 최신 행이라는 이유만으로 미래 기준일 또는 미확정 데이터를 사용하지 않는다.
- feature 누락과 실제 0값을 구분한다.
- `NULL`, `0`, 음수, 문자열 상태를 임의로 같은 의미로 처리하지 않는다.
- 입력 컬럼명과 table 구조를 추정하지 않는다.
- 계약 변경 전에는 loader, evaluator, repository와 downstream 영향을 함께 확인한다.

## 5. 출력과 상태 계약

| 출력 | 의미 |
|---|---|
| `strategy_daily_run` | daily buy 판단 실행 단위와 최종 상태 |
| `strategy_daily_signal` | BUY 후보와 sizing 결과 |
| `strategy_block_watch_candidate` | BLOCK 시장의 관찰 후보 |
| `strategy_daily_position_decision` | 포지션 HOLD, SELL, SKIP 판단 |
| `strategy_position_state` | 포지션의 최신 평가 상태 |

아래 계약은 명시 요청 없이 변경하지 않는다.

- table과 column 이름
- unique key와 conflict key
- insert, update, delete와 upsert 범위
- run status와 decision status 문자열
- market signal, BUY, BLOCK, HOLD, SELL, SKIP 의미
- reason code와 reason 문자열
- evaluator version과 engine version
- downstream이 읽는 필드와 정렬 기준

상태 처리 원칙:

- 시작, 완료, 실패 상태의 전환 조건을 확인한다.
- 일부 signal 저장 후 run만 성공 처리되는 부분 성공을 만들지 않는다.
- 예외를 catch한 뒤 성공 상태로 덮지 않는다.
- 재실행 시 동일 run date와 data date의 중복 또는 잔존 row를 확인한다.
- delete 후 insert 구조라면 삭제 범위와 transaction 경계를 먼저 확인한다.
- repository 호출 순서 변경 시 partial commit 가능성을 점검한다.

## 6. Market, Filter와 Sizing 규칙

- market 판단은 `port_strategy_common` 결과를 Decision 형식으로 adapter 처리한다.
- market signal, base exposure, max positions, min score와 flow 기준의 의미를 유지한다.
- market이 BLOCK이면 정상 BUY signal을 생성하지 않는다.
- BLOCK watch는 BUY 우회 경로가 아니라 관찰용 별도 산출물이다.
- buy filter의 score, quality, flow, toxic guard 기준을 임의로 재해석하지 않는다.
- sizing은 available cash, exposure, max positions, 최소 주문 단위와 haircut 의미를 보존한다.
- float 변환 실패나 결측을 조용히 0으로 바꾸기 전에 기존 계약을 확인한다.
- 후보 순서와 동점 처리 변경은 실제 주문 후보가 달라질 수 있으므로 기능 변경으로 취급한다.

## 7. Position Decision 규칙

- v1과 v2 evaluator를 같은 구현으로 간주하지 않는다.
- hard stop, 최소·최대 보유일, market BLOCK, 품질 저하와 수익권 HOLD 조건을 구분한다.
- v2는 daily 운영 검증을 먼저 수행한 뒤 common sell 결과를 mapping하는 구조를 유지한다.
- broker snapshot 누락과 실제 미보유를 구분한다.
- active position, position state와 broker position의 ticker·수량 정합을 확인한다.
- SELL 판단 생성과 실제 주문 실행을 같은 책임으로 표현하지 않는다.
- position state latest 갱신 시 과거 decision 이력을 덮어쓰지 않는다.
- evaluator version, reason과 priority 변경은 StrategyExecution 또는 운영 검증에 영향을 줄 수 있다.

## 8. `port_strategy_common` 의존성

이 저장소는 핵심 판단 로직을 공통 모듈에서 재사용한다.

| 영역 | 주요 공통 계약 |
|---|---|
| Config | strategy name, engine version, market·filter·sizing 설정과 snapshot |
| Market | common market context와 market decision |
| Filter | common buy candidate filter |
| Sizing | common position allocation |
| Guard | buy guard와 size haircut |
| BLOCK Watch | block watch candidate 평가 |
| Sell | common backtest sell decision |

다음 항목은 다른 서비스와 연결되므로 명시 요청 없이 변경하지 않는다.

- public 함수명과 import path
- dataclass 필드와 기본값
- enum과 상태 문자열
- reason code와 reason 문구
- config key와 snapshot 형식
- common 결과를 daily 형식으로 변환하는 mapping

공통 모듈 변경이 필요하면 이 저장소만 수정해 해결하지 않는다. 호출부와 공통 모듈의 책임을 분리해 보고한다.

## 9. Database 규칙

- DB 설정은 `db_config.py`의 실제 구현을 기준으로 확인한다.
- 환경변수 이름, 기본값, 필수값을 추정하지 않는다.
- password 기본값을 새로 만들지 않는다.
- 민감정보는 환경변수 또는 local secret loader를 사용한다.
- `search_path` 순서 변경은 unqualified SQL 해석에 영향을 주므로 계약 변경으로 취급한다.
- schema-qualified SQL과 search path 기반 SQL을 혼용할 때 대상 schema를 확인한다.
- column, unique key와 conflict target은 코드와 DDL 근거 없이 추정하지 않는다.
- SQL 쓰기 변경 전 insert, update, delete, upsert와 transaction 범위를 확인한다.
- commit과 rollback 위치를 확인하고 부분 저장 가능성을 보고한다.
- 실제 DB 접속 없이 정적 확인만 한 경우 AS-IS 검증 완료로 표현하지 않는다.

## 10. 실행과 운영 안전

사용자가 명시하지 않은 경우 아래 작업은 금지한다.

| 금지 작업 | 이유 |
|---|---|
| `daily_buy_signal_run.py` 실행 | signal과 run 데이터가 생성·갱신될 수 있음 |
| `daily_position_signal_run.py` 실행 | position decision과 state가 갱신될 수 있음 |
| `backtest_decision_run.py` 실행 | DB feature 조회가 발생함 |
| `daily_validator.py` 실행 | DB 조회와 민감정보 출력 가능성이 있음 |
| backtest 또는 research 실행 | 연구 데이터와 DB 접근 영향이 있음 |
| DB DDL·DML | 운영 계약과 데이터 변경 위험 |
| execution order 생성 | StrategyExecution 후속 흐름에 영향 |
| broker 주문·취소 | 실제 주문 영향 |
| Crawler와 Preprocessor 실행 | upstream 데이터 변경 위험 |
| 외부 API 호출 | 네트워크와 외부 시스템 영향 |
| AWS CLI·SDK 실행 | ECS, Step Functions와 운영 자원 영향 |
| Scheduler 변경 | 자동 실행 시각과 운영 흐름 영향 |
| Slack 전송 | 운영 알림 오발송 위험 |

문서 작업에서는 Python module import도 자동 실행이나 DB 연결 가능성을 확인하기 전에는 수행하지 않는다.

### 10.1 실행 모드 안전 규칙

운영 모드와 `--shadow` 모드를 명확히 구분한다.

| 항목 | 기준 |
|---|---|
| Shadow Transaction | read-only, write count 0 계약 유지 |
| Shadow 결과 | CloudWatch 구조화 JSON으로 출력 |
| Shadow 연계 | StrategyExecution·주문 경로에 연결하지 않음 |
| Family 분리 | 운영 Task Definition과 Shadow Family를 분리 |
| 운영 Command | `--shadow`를 혼입하지 않음 |
| Position 기본 | 운영 기본은 v1이며 Shadow v2 검증과 혼동하지 않음 |

## 11. 코드 수정 규칙

- 사용자의 명시 요청 없이 Python, Dockerfile, requirements와 설정 파일을 수정하지 않는다.
- 기존 함수 signature, CLI option과 module entrypoint를 유지한다.
- `python -m port_strategy_decision.xxx` 실행 구조를 깨지 않는다.
- 원본 Python 파일의 대규모 문자열 치환을 피하고 국소 수정한다.
- 사용자 변경을 되돌리지 않는다.
- 추정으로 legacy 파일을 삭제하지 않는다.
- 파일이 사용되지 않는 것처럼 보여도 import, Docker CMD, wrapper와 외부 호출 증거를 먼저 확인한다.
- 실패 후 무조건 SUCCESS를 출력하는 흐름을 만들지 않는다.
- 코드 수정 후에도 운영 실행이 필요한 검증은 수행하지 않고 한계로 남긴다.

## 12. 테스트와 검증

테스트가 있다면 DB와 운영 시스템을 격리한 정적·단위 검증을 우선한다.

| 영역 | 우선 검증 |
|---|---|
| Loader | run date, data date, 누락 feature와 기준일 정합 |
| Market | market signal과 제한값 mapping |
| Filter | 경계 점수, 결측과 후보 순서 |
| Sizing | available cash, exposure, 최대 보유 수와 rounding |
| BLOCK Watch | BUY 미생성, watch 후보 저장 범위 |
| Position v1 | stop, hold day, BLOCK과 quality 조건 |
| Position v2 | 선행 검증과 common sell mapping |
| Repository | unique key, upsert, delete 범위와 rollback |
| 재실행 | 동일 기준일 중복과 idempotency |

검증 원칙:

- DB가 필요한 테스트는 connection과 cursor를 mock 또는 fixture로 대체한다.
- 실제 broker snapshot, 주문과 운영 DB를 사용하지 않는다.
- 테스트가 import 시 DB나 외부 호출을 수행하는지 먼저 확인한다.
- 실행하지 못한 테스트를 통과로 기록하지 않는다.
- 문서만 수정한 경우 문서 형식과 변경 범위만 검증한다.

## 13. AWS와 컨테이너 규칙

- `Dockerfile`의 base image, package path, Common Wheel 설치와 CMD를 실제 파일 기준으로 확인한다.
- 기본 CMD와 Step Functions command override를 혼동하지 않는다.
- repository 안의 Dockerfile은 실행 이미지 정의이며 배포 완료 증거가 아니다.
- ECS RunTask, task definition, ECR image와 Step Functions 상태는 외부 운영 사실로 분리한다.
- 실제 cluster, task definition ARN, image URI, subnet, security group, IAM role과 secret ARN을 문서에 원문으로 기록하지 않는다.
- `port_strategy_common`은 vendoring이 아니라 1.0.0 Wheel 설치 구조이며, `.devops/packages/*.whl`은 git-ignore된 빌드 산출물임을 구분해 기록한다.

### 13.1 DevOps 검증 규칙

| 항목 | 기준 |
|---|---|
| Source·Image 정합 | Source SHA, Image Tag와 Digest 정합 확인 |
| PUSH_IMAGE | `false`는 품질 게이트, `true`는 ECR Push 목적으로 구분 |
| Shadow 실행 | Shadow Standalone 실행과 Shadow State Machine 실행을 구분 |
| 운영 승격 | Revision 등록과 활성 참조 전환을 구분 |
| 승격 검증 | 승격·Rollback·재승격 시 관련 State Machine 전체 참조 확인 |
| E2E 성공 | State Machine 성공, ECS Exit Code 0, 예상 Revision·Image 실행과 로그 확인 |
| Container 판정 | `EssentialContainerExited` 문자열만으로 실패 판정하지 않고 Exit Code 확인 |
| 범위 확인 | 운영 E2E에서 Step 8 이후와 주문 경로 미호출 확인 |
| 결과 구분 | 결과 0건과 검증 실패를 구분 |
| 실데이터 한계 | 실데이터 미발생 시 로직 동일성 검증 완료로 기록하지 않음 |

### 13.2 Decision Comparison 규칙

| 항목 | 기준 |
|---|---|
| Comparator 결과 | `MATCH`, `DIFFERENCE`, `REVIEW_REQUIRED`, `INVALID` 의미를 임의로 변경하지 않음 |
| 결과 혼동 금지 | `INVALID`와 `REVIEW_REQUIRED`를 같은 의미로 다루지 않음 |
| INVALID | 정상 Comparison으로 취급하지 않고 Promotion 대상에서 제외 |
| Evaluator 경계 | 운영 v1과 Shadow v2 구분을 유지 |
| Candidate Shadow | read-only, write_count=0 계약 유지 |
| Promotion Command | 운영 Command에 `--shadow`나 Shadow v2를 혼입하지 않음 |
| DB 영향 | Comparator 수정 시 운영 DB write를 추가하지 않음, 비교 결과를 Decision 판단 결과로 저장하지 않음 |
| Workflow 변경 | Comparison·Approval·Promotion 변경 시 Candidate Artifact identity와 운영 5개 State Machine 영향을 확인 |
| 문서 연동 | Comparison 파일 추가·책임 변경 시 `docs/source-file-catalog.md`를 함께 갱신 |

## 14. 보안과 민감정보

- password, token, API key, 계좌번호, webhook URL과 실제 DB 접속정보를 출력하거나 문서화하지 않는다.
- 발견한 민감정보는 값 자체를 인용하지 않고 존재와 위치만 보고한다.
- 예시 값은 `[REDACTED]` 또는 명백한 placeholder를 사용한다.
- broker order number, command id와 execution ARN 전체값을 문서에 남기지 않는다.
- 로그나 dump에 계좌, 종목별 보유 수량과 주문 정보가 있으면 필요한 최소 사실만 요약한다.
- 전체 ARN, IAM Role ARN, Policy ARN, Task ARN과 Execution ARN을 기록하지 않는다.
- AWS Account ID, subnet, security group과 전체 Image Digest를 기록하지 않는다.
- State Machine Definition 백업 등 로컬 임시 경로를 기록하지 않는다.
- DevOps 사실은 아래 안전 수준만 사용한다.

| 허용 항목 | 예 |
|---|---|
| Task Definition | Family와 Revision |
| State Machine | 이름 |
| Source | 단축 SHA |
| Image | Tag와 단축 Digest |
| 상태 | 성공·실패, Exit Code, Write Count |

## 15. 문서 갱신 규칙

### 15.1 README.md

다음이 바뀐 경우에만 필요한 부분을 갱신한다.

- 서비스 책임과 다른 MS의 경계
- 주요 entrypoint와 실행 흐름
- 입력·출력 table 계약
- 설정과 환경변수
- common 의존성과 adapter 구조
- Docker CMD와 컨테이너 실행 방식
- 외부 의존성 또는 안전 제약

### 15.2 CHANGELOG.md

- 실제 변경만 날짜별로 기록한다.
- 과거 시점의 worklog 생성, 파일 삭제와 DB 외부화 기록은 당시 사실이므로 보존한다.
- 문서 재정비와 Python 기능 변경을 구분한다.
- 실제 실행하지 않은 DB, AWS, 주문 검증을 완료로 기록하지 않는다.
- 반복되는 실행 금지 문장은 날짜별 Security 또는 Notes 표로 짧게 통합할 수 있다.

### 15.3 docs/source-file-catalog.md

다음 변경이 확인되면 관련 행이나 섹션을 함께 갱신한다.

| 변경 | 갱신 내용 |
|---|---|
| 파일 생성·삭제·이름 변경 | 파일 목록과 역할 |
| entrypoint 변경 | 실행 위험과 호출 관계 |
| loader·repository 책임 변경 | 입출력과 DB 영향 |
| common 의존성 변경 | 공통 함수와 adapter 책임 |
| table·상태 계약 변경 | 주요 입력·출력과 downstream 영향 |
| Docker·wrapper 변경 | 실행 이미지와 운영 wrapper 역할 |
| 문서 생성·삭제 | Documents 목록과 역할 |

내부 구현만 바뀌고 파일 책임과 변경 영향이 같으면 catalog를 수정하지 않는다.
카탈로그는 전체 파일 inventory가 아니라 운영과 유지보수에 중요한 책임 문서로 유지한다.

### 15.4 Worklog

- `docs/worklog`와 날짜별 worklog는 새로 만들지 않는다.
- 과거 CHANGELOG에 남은 worklog 생성 이력은 당시 사실이므로 삭제하지 않는다.
- 현재 작업 이력은 CHANGELOG에 필요한 핵심 변경만 남긴다.

## 16. 문서 정합성

네 문서는 같은 용어와 책임 경계를 사용해야 한다.

| 용어 | 기준 |
|---|---|
| 서비스명 | `port_strategy_decision` |
| 계층명 | Decision |
| upstream | Preprocessor |
| downstream | StrategyExecution |
| 시장 판단 | market decision |
| 매수 산출물 | daily BUY signal |
| 차단 시장 | BLOCK |
| 관찰 산출물 | block watch candidate |
| 포지션 판단 | HOLD, SELL, SKIP |
| 기준일 | run date와 data date를 구분 |
| 저장 방식 | insert, update, delete, upsert를 구체적으로 표기 |
| 외부 운영 | Scheduler, Step Functions, ECS RunTask를 repository 사실과 분리 |

코드에서 확인되지 않은 상태, table, column과 운영 구조를 문서 편의를 위해 추가하지 않는다.

## 17. Git 규칙

- 작업 전후 사용자 변경을 보존한다.
- `git status --short`와 `git diff --stat`은 변경 범위 확인에만 사용한다.
- 가능하면 `git diff --check`로 공백 오류를 확인한다.
- 명시 요청 없이 `git add`, `commit`, `push`, `reset`, `restore`, `checkout`을 실행하지 않는다.
- 저장소가 없는 첨부 파일 작업에서는 Git 검증을 수행한 것처럼 보고하지 않는다.

## 18. 완료 조건

작업 완료 전 아래를 확인한다.

- 대상 파일만 수정했는가
- Decision 책임과 다른 MS의 경계를 유지했는가
- total feature 입력과 strategy 출력 계약을 보존했는가
- BUY, BLOCK watch, HOLD, SELL과 SKIP 의미를 혼동하지 않았는가
- v1과 v2 evaluator 차이를 유지했는가
- common public 계약을 임의로 바꾸지 않았는가
- DB 쓰기와 재실행 위험을 확인했는가
- 문서 역할과 용어가 네 문서에서 일치하는가
- source catalog 갱신 조건에 해당하는지 확인했는가
- 신규 worklog를 만들지 않았는가
- 민감정보 원문을 새로 기록하지 않았는가
- UTF-8 No BOM, 300자 셀과 500자 라인 기준을 지켰는가
- 실행하지 않은 검증을 성공으로 보고하지 않았는가

## 19. 완료 보고

완료 보고는 2컬럼 표 중심으로 짧게 작성한다.

| 항목 | 보고 내용 |
|---|---|
| 변경 파일 | 실제 수정 파일 |
| 변경 요약 | 책임, 계약과 문서 구조의 핵심 변경 |
| 검증 결과 | 정적 확인과 실행한 안전 검증 |
| 미수행 | DB, AWS, signal과 주문 관련 미실행 항목 |
| 남은 위험 | 코드 대조 또는 운영 확인이 필요한 사항 |
| 민감정보 | 원문 신규 기록 여부 |

문서 수정 외 실제 운영 실행은 사용자가 명시적으로 요청하고 승인한 경우에만 수행한다.

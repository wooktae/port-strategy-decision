# CHANGELOG

`port_strategy_decision`의 기능, 데이터 계약, 실행 구조와 문서 기준 변경 이력을 기록한다.

- 최신 변경을 위에 배치한다.
- 기능 변경과 문서 정비를 구분한다.
- 민감정보와 일회성 운영값은 기록하지 않는다.
- 날짜별 worklog는 새로 만들지 않고 주요 변경은 이 문서에 남긴다.

## 2026-08-10

### Repository·Branch

| 항목 | 값 |
|---|---|
| 기본 브랜치 | `master` → `main` 전환 |
| OIDC Trust | main branch 기준 정리 |
| 최종 작업 단축 SHA | `a01d90592a7c` |

### Decision Comparison 자동화

| 항목 | 값 |
|---|---|
| 추가 파일 | `decision_comparator.py` |
| 책임 | 운영 DB 결과와 Shadow CloudWatch JSON 비교, report JSON 생성 |
| 비교 대상 | BUY와 Position |
| DB 영향 | 운영 DB read-only 조회, Decision 결과 신규 저장 없음 |
| 결과 4종 | MATCH, DIFFERENCE, REVIEW_REQUIRED, INVALID |
| INVALID 처리 | 실패 경로, Promotion 차단 |

### Candidate Shadow와 Comparator Runner

| 항목 | 값 |
|---|---|
| 추가 파일 | `decision_comparison_ecs_run.py` |
| 책임 | gzip+base64 Shadow JSONL 복원 후 comparator 실행, base64 report marker 출력 |
| Candidate 실행 | 운영과 분리된 Shadow Family에 Candidate Image Revision 등록 |
| 실행 방식 | GitHub Workflow ECS RunTask로 BUY Shadow → Position Shadow 직접 실행 |
| Shadow 계약 | read-only, write_count=0, 주문 경로 미연계 |
| BUY Shadow 보강 | Shadow BUY JSON에 비교용 `target_qty` 포함 |

### GitHub Approval과 Production Promotion

| 항목 | 값 |
|---|---|
| Workflow | Candidate Shadow → Comparison → Job Summary → production 승인 → Promotion 연결 |
| 승인 gate | GitHub `production` Environment manual approval |
| Reject | Promotion 미실행 확인 |
| Approve | Production Promotion 실행 확인 |
| Promotion Image | 승인된 동일 Candidate Image 재빌드 없이 사용 |
| BUY 운영 Command | `daily_buy_signal_run` 유지 |
| Position 운영 Command | 기본 v1 `daily_position_signal_run` 유지 |
| Revision 전환 | 기존 운영 `:3` 기준 신규 Revision 등록·전환 |
| 대상 State Machine | 관련 5개 운영 State Machine 참조 갱신·검증 |

### Validation

| 항목 | 값 |
|---|---|
| 실데이터 Comparison | 2026-08-10 실데이터로 성공 |
| Market | 운영·Shadow 모두 BLOCK, MATCH |
| BUY Shadow Signal | 0건 |
| Shadow Position Decision | 3건, write_count=0 |
| 최종 결과 | `REVIEW_REQUIRED` |
| Review 분류 | 7건 Position 비교가 사람 확인 필요로 분류 |
| 차이 예시 | 운영 HOLD → Shadow SELL, Shadow 평가 대상에서 제거된 Position |
| 해석 | 운영 v1 vs Shadow v2와 active position population 차이 탐지, 판단 오류 아님 |
| 전체 Workflow | Comparison → 승인 → Production Promotion까지 성공 |

### 작업 범위

| 항목 | 값 |
|---|---|
| 전략 판단 로직 변경 | 없음, 운영 Position 기본 v1 유지 |
| 신규 기능 | Comparison 자동화와 Comparator ECS Runner |
| Shadow 보강 | BUY Shadow JSON `target_qty` 추가 |
| 운영 DB 영향 | 없음, Comparison은 read-only |
| 주문 실행 | 없음 |
| 이번 문서 작업 | `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/source-file-catalog.md` 현행화 |
| 민감정보 | 전체 ARN·Digest·Account ID·subnet·security group·로컬 경로 원문 기록 없음 |

## 2026-07-31

### Decision DevOps 기준선

| 항목 | 값 |
|---|---|
| GitHub Repository | `wooktae/port-strategy-decision` |
| 기본 브랜치 | `master` |
| Source 정합성 | Local·Remote·CodeBuild Source SHA 일치 확인 |
| Source 단축 SHA | `ff4d285b87b9` |
| ECR Image Tag | `ff4d285b87b9` |
| Image 단축 Digest | `3be7251875f9` |
| Common 의존성 | `port_strategy_common` 1.0.0 Wheel 설치 |

| CI 품질 게이트 | 내용 |
|---|---|
| Python Compile | `compileall` |
| Unit·Contract Test | import contract, position evaluator version contract |
| Static Analysis | Ruff |
| Host Smoke | Import·Entrypoint smoke |
| Container Smoke | Import·Entrypoint smoke |
| Docker Build | 이미지 build |
| ECR Push | `PUSH_IMAGE=true` 실행에서만 push |

| 항목 | 값 |
|---|---|
| GitHub Actions | `workflow_dispatch` 트리거 |
| 인증 | GitHub OIDC 기반 CodeBuild 실행 |
| Source 전달 | GitHub Commit SHA를 CodeBuild Source Version으로 전달 |

### Shadow Canary

| 항목 | 값 |
|---|---|
| Family 분리 | BUY·Position 각각 운영과 분리된 Shadow Family |
| Shadow Revision | 각각 `:1` |
| BUY Shadow | 운영 진입점에 `--shadow` 추가 |
| Position Shadow | `--shadow --evaluator-version v2` |
| 저장 계약 | read-only, write_count=0 |
| 결과 | CloudWatch 구조화 JSON |
| State Machine | Shadow 전용 State Machine에서 BUY → Position 순차 실행 |
| 실행 결과 | State Machine SUCCEEDED, 두 Container Exit Code 0 |
| 주문 연계 | 운영 Step Functions·StrategyExecution·주문과 미연계 |

| 항목 | 값 |
|---|---|
| 초기 실패 | Step Functions Role의 Shadow Family `ecs:RunTask` 권한 누락 |
| 보완 | 운영 권한 보존 상태로 Shadow Family 권한만 최소 추가 |
| 재실행 | 권한 보완 후 재실행 성공 |
| Managed Policy | 기본 버전 v3 → v4 |
| 실데이터 한계 | 입력 BLOCK·Position 0건으로 v1·v2 실차이 비교 제한, 추가 비교 필요 |

1차 Shadow 결과는 Run Date·Data Date 정합 확인, Market Signal BLOCK, BUY Candidate·Signal·Block Watch 0건, 활성 Position·HOLD·SELL·SKIP 0건, Position Shadow Evaluator v2 기준 BUY·Position write_count 모두 0이었다.

### 운영 승격과 Rollback

| 항목 | 값 |
|---|---|
| 운영 BUY Revision | `:2` → `:3` 등록 |
| 운영 Position Revision | `:2` → `:3` 등록 |
| 운영 Command | Shadow 옵션 없음 |
| 신규 Image | Tag `ff4d285b87b9`, 단축 Digest `3be7251875f9` |
| 대상 State Machine | Decision Revision 참조 5개 |
| 승격 | `:2` → `:3` 전환과 활성 참조 확인 |
| Rollback | `:3` → `:2` 복구와 이전 Revision 참조 확인 |
| 재승격 | `:2` → `:3` 재전환과 최종 Revision `:3` 참조 확인 |
| Shadow 유지 | Shadow Revision `:1` 유지 |

대상 5개 State Machine은 `portfolio-paper-daily-step1-11-safe`, `portfolio-paper-daily-step1-17-approval`, `portfolio-paper-daily-step6-only`, `portfolio-paper-daily-step6-step7-step8-step9-step10-step11`, `portfolio-paper-daily-step7-only`다. 승격·Rollback·재승격은 동일 Image Digest를 재빌드 없이 사용했다.

### 운영 E2E

| 항목 | 값 |
|---|---|
| BUY 실행 | `portfolio-paper-daily-step6-only` SUCCEEDED |
| Position 실행 | `portfolio-paper-daily-step7-only` SUCCEEDED |
| 실행 Revision | 운영 BUY·Position Revision `:3` |
| Container | 두 실행 모두 Exit Code 0 |
| Image | 예상 Tag·Digest 일치 |
| 로그 | CloudWatch 확인, 오류 패턴 0건 |
| Daily Run | Run ID 86 사용 |
| BUY 결과 | Market Signal BLOCK, Candidate·Signal 0건 |
| Position 결과 | 운영 Evaluator v1, Position·Decision 0건 |
| 실행 범위 | Step 6·7만 실행, Step 8~17·StrategyExecution·주문 미실행 |

이 E2E는 Decision 단계까지의 검증이다. 전체 Paper Daily Step 1~17이나 주문 체결까지 검증한 것이 아니다. 0건 결과는 입력 조건에 따른 정상 결과이며 검증 실패가 아니다.

### 후속 과제

| 항목 | 값 |
|---|---|
| 자동 비교 | 운영 DB 결과와 Shadow JSON 자동 Comparison Task (미구현) |
| BUY 비교 | BUY 종목·수량 발생일의 실데이터 비교 |
| Position 비교 | HOLD·SELL·SKIP 발생일의 v1·v2 실데이터 비교 |
| 검토 | 판단 사유 차이에 대한 Decision 개발팀 검토와 승격 기준 정교화 |

Comparison Task는 완료가 아니라 후속 과제다.

### 작업 범위

| 항목 | 값 |
|---|---|
| 전략 판단 로직 변경 | 없음 |
| Shadow 실행 기능 | 진입점 `--shadow` read-only 모드 |
| CI·Container 배포 구성 | workflow, buildspec, smoke script, contract test 추가 |
| AWS 변경 | Task Definition Revision, Shadow·운영 State Machine, IAM 최소 권한 |
| 운영 DB 영향 | 없음 (Shadow read-only, 운영 E2E 결과 0건) |
| 주문 실행 | 없음 |
| 이번 문서 작업 | `AGENTS.md`, `README.md`, `CHANGELOG.md` 현행화 |
| 민감정보 | 전체 ARN·Digest·Account ID·로컬 경로 원문 기록 없음 |

## 2026-07-22

### Decision 문서 기준 재정비

| 항목 | 값 |
|---|---|
| 변경 범위 | `AGENTS.md`, `README.md`, `CHANGELOG.md`, `docs/source-file-catalog.md` 문서 정합성 정비 |
| 기능 변경 | 없음 |
| 코드·설정 변경 | 없음 |
| DB·AWS 실행 | 없음 |
| 운영 데이터 변경 | 없음 |

### AGENTS.md

| 항목 | 변경 내용 |
|---|---|
| 최우선 규칙 | 가독성, 2열 표, 긴 셀 분리와 문서 중복 방지 기준을 문서 앞부분에 배치 |
| 작업 범위 | `port_strategy_decision` 내부 작업과 다른 MS read-only 원칙을 명확화 |
| 책임 경계 | Decision과 Crawler, Preprocessor, StrategyExecution, MarketConnector, View, Research의 책임을 분리 |
| Daily Buy | feature loading, market, filter, sizing, BUY signal과 BLOCK watch 흐름을 구분 |
| Position | v1·v2 evaluator와 HOLD·SELL·SKIP 판단 책임을 구분 |
| 데이터 계약 | total feature 입력과 daily run, signal, watch, position decision 출력 계약을 정리 |
| Common 계약 | public 함수, dataclass, enum, 상태값과 reason 문자열 변경 제한을 명시 |
| DB 안전 | unique key, upsert, delete 범위, transaction과 재실행 영향 확인 기준을 추가 |
| 상태 안전 | 부분 성공, 예외 후 성공 처리와 중복 저장 방지 원칙을 추가 |
| 실행 제한 | daily signal, backtest, DB 쓰기, AWS, 주문과 외부 호출 금지 범위를 구체화 |
| 문서 연동 | 파일 책임이 바뀌면 `docs/source-file-catalog.md`도 함께 갱신하도록 명시 |
| Worklog | 날짜별 worklog 신규 생성 금지로 현행 문서 운영 기준을 변경 |

### README.md

| 항목 | 변경 내용 |
|---|---|
| 문서 목적 | 작업 규칙보다 현재 구조와 운영 AS-IS 설명에 집중하도록 재구성 |
| 서비스 요약 | 계층, 주요 입력, 출력, 진입점과 외부 의존성을 첫 요약 표에 배치 |
| Daily Buy 흐름 | total feature에서 market, filter, sizing, BUY 또는 BLOCK watch로 이어지는 흐름을 정리 |
| Position 흐름 | daily run, active position, broker snapshot과 feature를 결합한 HOLD·SELL·SKIP 흐름을 정리 |
| BUY·SELL 의미 | Decision 산출물과 실제 주문 제출 책임이 다름을 명확화 |
| 입력 계약 | market feature, stock feature, universe와 broker snapshot의 역할을 분리 |
| 출력 계약 | daily run, signal, block watch, position decision과 position state를 구분 |
| 파일 구조 | 중첩 장문 목록을 역할별 2열 표 중심으로 재구성 |
| Common 의존성 | market, filter, sizing, guard와 sell 재사용 지점을 정리 |
| AWS 위치 | Paper Daily Step 6과 Step 7에서의 실행 위치를 구분 |
| 컨테이너 | 기본 CMD, command override, Common vendoring과 배포 책임을 정리 |
| DB 설정 | `INTEREST_DB_*`, 기본 DB와 search path 설명을 표 중심으로 정리 |
| 상태 주의 | 부분 성공, 재실행, 누락 feature, transaction과 최신성 주의사항을 보강 |
| 문서 체계 | AGENTS, README, CHANGELOG와 source catalog의 역할을 구분 |

### docs/source-file-catalog.md

| 항목 | 변경 내용 |
|---|---|
| 구성 기준 | 파일별 장문 목록을 흐름, 입출력, DB 영향과 실행 위험 중심으로 유지 |
| 갱신 조건 | 파일, entrypoint, table, Common과 Docker 변경 시 catalog 연동 기준 명시 |
| Worklog | 날짜별 worklog 미생성 유지, `docs`에는 source catalog만 유지 |

### 실제 코드 대조 반영

| 항목 | 변경 내용 |
|---|---|
| `stock_universe` | Daily 입력 역할을 company_name 보강용 LEFT JOIN 대상으로 정정 |
| `connector_balance_snapshot` | Daily Buy 가용 현금 입력이 아니라 Position 평가의 최신 broker snapshot 기준일 확인 역할로 정정 |
| Daily Buy 처리 | `daily_buy_signal_run` 실행 흐름 설명에서 미호출 guard 단계를 제외 |

### 문서 운영 결정

| 항목 | 값 |
|---|---|
| 신규 worklog | 생성하지 않음 |
| 과거 worklog 기록 | 당시 변경 사실이므로 CHANGELOG에서 보존 |
| 상세 파일 책임 | `docs/source-file-catalog.md`에서 관리 |
| 실제 코드 대조 | entrypoint, loader, repository와 evaluator 정적 확인으로 4개 문서 정합성 점검 완료 |
| 민감정보 | 원문 기록 금지 |
| 일회성 운영값 | CHANGELOG 기록 대상에서 제외 |

## 2026-07-01

### AWS 운영 위치와 책임 경계 문서화

| 항목 | 변경 내용 |
|---|---|
| README | Decision 책임 경계, AWS 운영 위치와 컨테이너 이미지 설명 추가 |
| 실행 형식 | 실행 예시를 `python -m port_strategy_decision.<module>` 형식으로 정정 |
| Step 6 | Daily Buy Signal 진입점을 `daily_buy_signal_run.py` 기준으로 정리 |
| Step 7 | Position Signal 진입점을 `daily_position_signal_run.py`와 v1·v2 evaluator 기준으로 정리 |
| 서비스 경계 | Preprocessor, StrategyExecution, MarketConnector, View, Research, Scheduler와의 책임 분리 |
| Source catalog | `Dockerfile`, `requirements.txt`와 파일별 실행 위험 추가 |
| Worklog | 당시 문서 운영 기준에 따라 `docs/worklog/2026-07-01.md` 생성 |

### 작업 범위

| 항목 | 값 |
|---|---|
| 기능 변경 | 없음 |
| 코드·설정 변경 | 없음 |
| 실제 실행 | daily signal, backtest, execution order, DB DDL·DML, 외부 API, 크롤링과 주문 실행 없음 |
| 외부 MS 기록 | 이 저장소 범위 밖의 세부 운영 로그는 반영하지 않음 |
| 민감정보 | AWS 식별자, DB 접속값, 계좌와 주문번호 원문 기록 없음 |

## 2026-05-28

### 파일 카탈로그와 코드 설명 정비

| 항목 | 변경 내용 |
|---|---|
| Source catalog | 전체 파일 역할과 실행 주의사항을 정리한 `docs/source-file-catalog.md` 추가 |
| Python 설명 | 모듈 단위 한글 docstring과 핵심 파이프라인·DB 함수 설명 추가 |
| Backtest snapshot | `backtest_decision_run.py`에서 Common run store 의존성과 run 생성 호출 제거 |
| 실행 의미 | 단일 일자 market, filter와 sizing snapshot 출력 entrypoint로 정리 |
| 문서 정합성 | README와 source catalog에 DB feature 조회 기반 snapshot임을 반영 |
| 로컬 경로 | 파일 상단 로컬 절대 경로 주석을 모듈 역할 docstring으로 교체 |
| Worklog | 당시 문서 운영 기준에 따라 `docs/worklog/2026-05-28.md` 생성 |

### 작업 범위

| 항목 | 값 |
|---|---|
| Decision 기능 변경 | `backtest_decision_run.py`의 Common run 기록 의존 제거 |
| 실제 DB·운영 실행 | 없음 |
| 민감정보 | 문서와 주석에 기록하지 않음 |

## 2026-05-27

### DB 설정과 schema 구조 정비

| 항목 | 변경 내용 |
|---|---|
| DB 설정 | 로컬 `db_config.py`의 `get_db_config()`로 접속 설정 외부화 |
| 환경변수 | `INTEREST_DB_*` 기반 설정으로 정리 |
| Password | 하드코딩 후보 제거와 `INTEREST_DB_PASSWORD` 필수 검증 적용 |
| 기본 DB | 로컬 기본 DB명을 `interest_crawler`에서 `portfolio`로 변경 |
| Schema 구조 | 단일 DB `portfolio`와 domain별 schema 구조 문서화 |
| Search path | Decision 모듈의 schema 탐색 순서를 문서화 |
| SQL 호환 | 기존 SQL이 search path 기반으로 동작하는 구조를 유지 |

### 작업 범위

| 항목 | 값 |
|---|---|
| 실제 DB 실행 | 없음 |
| Daily·Backtest 실행 | 없음 |
| 외부 호출·주문 | 없음 |
| 민감정보 | 원문 기록 없음 |

## 2026-05-26

### 초기 문서와 로컬 후보 정리

| 항목 | 변경 내용 |
|---|---|
| 초기 문서 | `AGENTS.md`, `README.md`와 당시 worklog 초안 추가 |
| 캐시 정리 | Python `__pycache__/` 산출물 정리 |
| 테스트 후보 | ignored 상태의 로컬 test·debug 후보 9개 정리 |
| 보존 파일 | `backtest_decision_run.py`, `daily_validator.py`는 삭제하지 않고 보류 후보로 유지 |

### 정리한 로컬 test·debug 후보

| 파일 | 처리 |
|---|---|
| `test_compare_common_buy_filter.py` | 정리 |
| `test_compare_common_buy_sizing.py` | 정리 |
| `test_compare_common_buy_toxic_guard.py` | 정리 |
| `test_compare_common_market.py` | 정리 |
| `test_compare_common_sell_logic.py` | 정리 |
| `test_compare_daily_position_v1_v2.py` | 정리 |
| `test_daily_buy_toxic_haircut.py` | 정리 |
| `test_daily_position_v1_v2_synthetic.py` | 정리 |
| `test_debug_daily_buy_toxic.py` | 정리 |

### 작업 범위

| 항목 | 값 |
|---|---|
| 작성 기준 | 당시 로컬 파일 구조와 import·entrypoint 확인 결과 |
| 실제 실행 | daily signal, backtest, execution order, DB, 외부 API, 크롤링과 주문 실행 없음 |
| 민감정보 | 원문 기록 없음 |

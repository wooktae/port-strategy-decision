# CHANGELOG

`port_strategy_decision`의 기능, 데이터 계약, 실행 구조와 문서 기준 변경 이력을 기록한다.

- 최신 변경을 위에 배치한다.
- 기능 변경과 문서 정비를 구분한다.
- 민감정보와 일회성 운영값은 기록하지 않는다.
- 날짜별 worklog는 새로 만들지 않고 주요 변경은 이 문서에 남긴다.

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

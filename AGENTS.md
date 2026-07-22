# AGENTS.md - port_strategy_decision

## 프로젝트
- 이 저장소는 포트폴리오 전략의 daily decision 계층을 담당하는 Python 마이크로서비스 루트다.
- 주요 역할은 전처리된 total feature를 읽어 market decision, buy candidate filter, sizing, daily buy signal, daily position HOLD/SELL decision을 생성하는 것이다.
- `port_strategy_common`의 공통 market/filter/sizing/guard/sell 로직을 daily 및 backtest 성격의 decision 흐름에서 재사용한다.
- 현재 구조는 패키지 디렉터리보다 루트의 독립 실행형 Python 스크립트 중심이다.

## 작업 범위
- 현재 `port_strategy_decision` 루트 안에서만 작업한다.
- 현재 루트 밖 파일은 참고용으로만 읽고 수정하지 않는다.
- 코드 또는 문서 수정 전 현재 파일 구조와 실행 영향 범위를 먼저 확인한다.
- 변경은 작고 검증 가능한 범위로 유지한다.

## 허용 작업
- README / docs 작성 및 수정
- Python 스크립트 구조 분석
- import, entrypoint, DB 접근 지점, 공통 로직 의존성 확인
- daily buy signal, daily position signal, market/filter/sizing/decision, repository/loader/config 스크립트 구분
- 실행하지 않는 범위의 정적 분석과 문서화
- 명시 요청이 있는 경우에만 테스트 또는 디버그 코드 정리

## 금지 작업
- 실제 daily signal 실행 금지
- backtest 또는 research 실행 금지
- execution order 생성 실행 금지
- 주문 제출 또는 주문 실행 금지
- DB DDL/DML 직접 실행 금지
- 외부 API 호출 금지
- 크롤링 실행 금지
- 민감정보 값 출력 또는 문서 기록 금지
- 실제 로컬 운영 설정 파일 수정 금지
- 명시 승인 없는 파일 삭제 금지
- 명시 요청 없는 commit 금지

## 유지해야 할 것
- 기존 DB 테이블명, 컬럼명, unique key, upsert 정책
- `strategy_daily_run`, `strategy_daily_signal`, `strategy_daily_position_decision`, `strategy_position_state` 관련 계약
- `pre_total_market_daily_feature`, `pre_total_stock_daily_feature` 입력 feature 계약
- `port_strategy_common`의 public 함수명, dataclass 필드, enum/decision reason 문자열
- daily buy signal과 daily position decision의 기존 상태값 및 reason 문자열
- backtest와 daily 흐름이 공유하는 common market/filter/sizing/sell 판단 호환성

## 스크립트 구분 원칙
- daily buy signal 계열은 `daily_buy_signal_run.py`, `daily_signal_builder.py`, `daily_repository.py`, `daily_block_watch_builder.py`, `daily_block_watch_repository.py`, `daily_feature_loader.py` 중심으로 본다.
- daily position signal 계열은 `daily_position_signal_run.py`, `daily_position_evaluator.py`, `daily_position_evaluator_v2.py`, `daily_position_repository.py` 중심으로 본다.
- market/filter/sizing/decision 계열은 `backtest_market.py`, `backtest_filter.py`, `backtest_sizing.py`, `backtest_decision_run.py` 중심으로 본다.
- 검증/조회 후보는 `daily_validator.py`처럼 DB 조회 또는 출력이 포함될 수 있으므로 실행 전에 영향 범위를 확인한다.
- test/debug/output dump 파일은 운영 소스로 단정하지 않고 후보 또는 로컬 산출물로만 표현한다.

## 보안 규칙
- 비밀번호, 토큰, API key, 계좌번호, webhook URL, DB 접속정보 등 민감정보 값은 출력하거나 문서에 기록하지 않는다.
- 민감정보가 필요하면 `[REDACTED]`로 마스킹한다.
- 로컬 파일에서 민감정보를 발견해도 값을 인용하지 않는다.
- 예시 설정에는 실제 credential을 넣지 않는다.

## Git 규칙
- 작업 후 `git status --short`로 변경 범위를 확인한다.
- 작업 후 `git diff --stat`으로 변경 파일 범위를 확인한다.
- 사용자 변경을 되돌리지 않는다.
- 명시 요청 없이 commit하지 않는다.

## 검증 명령
문서만 수정한 경우:

```powershell
git status --short
git diff --stat
```

코드 수정 시에도 실제 daily signal, backtest/research, execution/order 생성, DB 쓰기, 외부 API, 크롤링, 주문 실행이 포함되지 않는 검증만 선택한다. 실행 위험이 있으면 완료 보고에 검증 한계를 남긴다.

## 완료 보고
작업 완료 후 아래 항목만 짧게 보고한다.

- 변경 파일
- 변경 요약
- 검증 결과
- 남은 위험 또는 후속 작업

## 문서화 규칙
- README.md는 프로젝트 이해, 실행 방법, 설정 방법, 주요 기능, 폴더 구조, 외부 의존성이 바뀐 경우에만 갱신한다.
- CHANGELOG.md에는 실제 변경된 주요 내용만 짧게 기록한다.
- docs/worklog/YYYY-MM-DD.md에는 작업 내용을 계획/완료 처리 형식으로 정리한다.
- worklog 작성 시 아래 들여쓰기 형식을 유지한다.
  - ` 1) 큰 작업 명` (앞 공백 1칸)
  - `   (1) 세부 작업` (앞 공백 3칸)
  - `       - 추가 설명` (앞 공백 7칸)
- `1.` 형식은 사용하지 않는다. markdown 자동 번호 목록으로 렌더링되어 들여쓰기와 상태 표기가 깨질 수 있다.
- 탭 문자를 섞지 않는다. 공백만 사용한다.
- 완료/예정/보류/실패/확인 상태를 작업 명 끝에 `:완료`, `:예정`, `:보류`, `:실패`, `:확인`으로 명확히 표시한다.
- 상태값은 `작업 명:완료`처럼 작업 명과 콜론 사이에 공백을 두지 않는다.
- 이미 작성된 과거 날짜 worklog의 기존 형식은 유지하고, 신규 날짜 worklog부터 위 규칙을 적용한다.

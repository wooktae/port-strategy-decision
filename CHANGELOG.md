# CHANGELOG

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

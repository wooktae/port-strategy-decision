"""매수 후보 필터 공통 로직 adapter 모듈.

stock feature 목록과 market decision을 `port_strategy_common` 필터 입력으로
맞춰 전달한다. 자체 DB 접근은 없으며, decision reason 문자열과 공통 설정
계약을 그대로 유지해야 한다.
"""

from __future__ import annotations

from decimal import Decimal

from port_strategy_common.config import FILTER_CONFIG
from port_strategy_common.common_result import CommonMarketDecision
from port_strategy_common.common_buy_filter import common_filter_buy_candidates


CFG = FILTER_CONFIG


def d(v, default="0"):
    if v is None:
        return Decimal(str(default))
    return Decimal(str(v))


def filter_buy_candidates(stock_rows, decision):
    """공통 buy filter를 호출해 daily/backtest 매수 후보를 선별한다."""
    common_decision = CommonMarketDecision(
        market_signal=decision.signal_type,
        base_exposure=float(decision.base_exposure),
        max_positions=decision.max_positions,
        min_score=float(decision.min_score),
        min_flow=float(decision.min_flow),
        reason=decision.reason,
        detail={},
    )

    return common_filter_buy_candidates(
        stock_rows=stock_rows,
        decision=common_decision,
        config=CFG,
    )

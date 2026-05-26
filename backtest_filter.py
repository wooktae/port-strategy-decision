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
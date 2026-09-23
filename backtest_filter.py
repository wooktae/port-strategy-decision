"""Adapter module for the shared buy-candidate filter logic.

Adapts the stock feature list and the market decision into the
`port_strategy_common` filter inputs. It has no DB access of its own, and it
must preserve the decision reason strings and the shared config contract as-is.
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
    """Call the shared buy filter to select daily/backtest buy candidates."""
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

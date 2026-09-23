"""Adapter module for the shared buy-candidate sizing logic.

Converts the filter-passed candidates and the market decision into the shared
sizing inputs. Position size calculation is delegated to `port_strategy_common`,
and it performs no DB access.
"""

from __future__ import annotations

from decimal import Decimal

from port_strategy_common.config import SIZING_CONFIG
from port_strategy_common.common_result import CommonMarketDecision
from port_strategy_common.common_buy_sizing import common_allocate_positions


CFG = SIZING_CONFIG


def d(v):
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def clamp(v, mn, mx):
    return max(mn, min(v, mx))


def allocate_positions(buy_candidates, market_decision):
    """Call the shared sizing logic to compute position_size for each candidate."""
    common_decision = CommonMarketDecision(
        market_signal=market_decision.signal_type,
        base_exposure=float(market_decision.base_exposure),
        max_positions=market_decision.max_positions,
        min_score=float(market_decision.min_score),
        min_flow=float(market_decision.min_flow),
        reason=market_decision.reason,
        detail={},
    )

    return common_allocate_positions(
        buy_candidates=buy_candidates,
        market_decision=common_decision,
        config=CFG,
    )

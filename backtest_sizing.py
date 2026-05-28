"""매수 후보 sizing 공통 로직 adapter 모듈.

필터를 통과한 후보와 market decision을 공통 sizing 입력으로 변환한다.
포지션 크기 계산은 `port_strategy_common`에 위임하며 DB 접근은 하지 않는다.
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
    """공통 sizing 로직을 호출해 후보별 position_size를 산출한다."""
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

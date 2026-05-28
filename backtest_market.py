"""시장 feature를 공통 market decision으로 변환하는 adapter 모듈.

`pre_total_market_daily_feature` row를 `port_strategy_common` 입력 컨텍스트로
바꾸고, daily/backtest 흐름이 공유할 `MarketDecision` 값을 반환한다.
DB 접근이나 외부 API 호출은 하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from port_strategy_common.config import MARKET_CONFIG
from port_strategy_common.common_context import CommonMarketContext
from port_strategy_common.common_market import common_decide_market


@dataclass
class MarketDecision:
    signal_type: str
    base_exposure: Decimal
    max_positions: int
    min_score: Decimal
    min_flow: Decimal
    reason: str


CFG = MARKET_CONFIG


def d(v):
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def evaluate_market(market: dict) -> MarketDecision:
    """공통 market 판단을 호출하고 decision 계층의 dataclass로 변환한다."""
    context = CommonMarketContext(
        trade_date=str(market.get("date", "TEST")),
        market_regime_score=float(d(market.get("market_regime_score"))),
        breadth_pressure_score=float(d(market.get("breadth_pressure_score"))),
        flow_pressure_score=float(d(market.get("flow_pressure_score"))),
        macro_pressure_score=float(d(market.get("macro_pressure_score"))),
        program_pressure_score=float(d(market.get("program_pressure_score"))),
        raw=dict(market),
    )

    decision = common_decide_market(context, CFG)

    return MarketDecision(
        signal_type=decision.market_signal,
        base_exposure=Decimal(str(decision.base_exposure)),
        max_positions=decision.max_positions,
        min_score=Decimal(str(decision.min_score)),
        min_flow=Decimal(str(decision.min_flow)),
        reason=decision.reason,
    )

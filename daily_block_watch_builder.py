from __future__ import annotations

from typing import Any

from port_strategy_common.common_block_watch import evaluate_block_watch_candidate


def _get_value(source: Any, *names: str) -> Any:
    if source is None:
        return None

    if isinstance(source, dict):
        for name in names:
            if name in source:
                return source.get(name)
        return None

    for name in names:
        if hasattr(source, name):
            return getattr(source, name)

    return None


def build_block_watch_candidates(
    *,
    daily_run_id: int,
    run_date,
    data_date,
    market_signal: str,
    stock_candidates: list[Any],
) -> list[dict[str, Any]]:
    """
    BLOCK 구간에서 강한 예외 후보를 관찰 대상으로 만든다.

    주의:
    - 이 함수는 BUY signal을 만들지 않는다.
    - 이 함수는 execution order를 만들지 않는다.
    - 결과는 strategy_block_watch_candidate 저장용이다.
    """

    if (market_signal or "").upper() != "BLOCK":
        return []

    watch_candidates: list[dict[str, Any]] = []

    for stock in stock_candidates:
        decision = evaluate_block_watch_candidate(
            market_signal=market_signal,
            stock_context=stock,
        )

        if not decision.is_watch:
            continue

        ticker_code = _get_value(stock, "ticker_code", "code", "symbol")
        stock_name = _get_value(stock, "stock_name", "name", "company_name")

        flow_score = _get_value(stock, "flow_score", "buy_flow_score", "supply_score")
        final_score = _get_value(stock, "final_score", "buy_final_score", "total_score")
        info_score = _get_value(stock, "info_score", "buy_info_score")
        volatility_20d = _get_value(stock, "volatility_20d", "vol_20d")
        intraday_range = _get_value(stock, "intraday_range", "day_range")
        short_pressure_score = _get_value(stock, "short_pressure_score", "short_pressure")
        close_price = _get_value(stock, "close_price", "price", "current_price")

        if ticker_code is None:
            continue

        watch_candidates.append(
            {
                "daily_run_id": daily_run_id,
                "run_date": run_date,
                "data_date": data_date,
                "ticker_code": ticker_code,
                "stock_name": stock_name,
                "market_signal": "BLOCK",
                "watch_status": "WATCH",
                "flow_score": flow_score,
                "final_score": final_score,
                "info_score": info_score,
                "volatility_20d": volatility_20d,
                "intraday_range": intraday_range,
                "short_pressure_score": short_pressure_score,
                "watch_reason": decision.watch_reason,
                "watch_detail": decision.watch_detail,
                "close_price": close_price,
            }
        )

    return watch_candidates
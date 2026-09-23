"""Builder module that assembles daily BUY signal rows.

Converts the sizing results and stock features into the `strategy_daily_signal`
storage format. DB persistence is handled by the repository, and the
status/reason string contract is not changed.
"""

from decimal import Decimal
from typing import Any

from port_strategy_common.config import STRATEGY_NAME, ENGINE_VERSION
from port_strategy_decision.daily_repository import to_jsonb


def _get(row: dict, *keys, default=None):
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]

    return default


def _to_decimal_or_none(value: Any):
    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except Exception:
        return None


def _to_float_or_none(value: Any):
    if value is None:
        return None

    try:
        return float(value)
    except Exception:
        return None


def _build_feature_snapshot(position: dict, stock: dict):
    return {
        "ticker_code": _get(position, "ticker_code") or _get(stock, "ticker_code"),
        "company_name": _get(position, "company_name") or _get(stock, "company_name"),
        "final_score": _to_float_or_none(_get(position, "score", "final_score") or _get(stock, "final_score")),
        "flow_score": _to_float_or_none(_get(position, "flow", "flow_score") or _get(stock, "flow_score")),
        "tape_score": _to_float_or_none(_get(position, "tape", "tape_score") or _get(stock, "tape_score")),
        "info_score": _to_float_or_none(_get(position, "info", "info_score") or _get(stock, "info_score")),
        "short_score": _to_float_or_none(_get(position, "short", "short_score", "short_pressure_score") or _get(stock, "short_score", "short_pressure_score")),
        "volatility_20d": _to_float_or_none(_get(position, "vol", "volatility_20d") or _get(stock, "volatility_20d")),
        "intraday_range": _to_float_or_none(_get(position, "intraday_range") or _get(stock, "intraday_range")),
        "position_size": _to_float_or_none(_get(position, "position_size")),
        "is_hot_chase": bool(_get(position, "is_hot_chase", default=False)),
        "has_info_flag": bool(_get(position, "has_info_flag", default=False)),
        "is_buy_day_stop_risk": bool(_get(position, "is_buy_day_stop_risk", default=False)),
        "is_flow_0_9_plus_soft": bool(_get(position, "is_flow_0_9_plus_soft", default=False)),
        "is_mid_flow_tight_range_risk": bool(_get(position, "is_mid_flow_tight_range_risk", default=False)),
    }


def _build_buy_info(position: dict, stock: dict, decision):
    snapshot = _build_feature_snapshot(position, stock)

    return {
        **snapshot,
        "entry_market_signal": getattr(decision, "signal_type", None),
        "base_exposure": str(getattr(decision, "base_exposure", "")),
        "max_positions": getattr(decision, "max_positions", None),
        "entry_source": "DAILY_SIGNAL",
    }


def _build_raw_features(stock: dict):
    raw = {}

    for key, value in stock.items():
        if isinstance(value, Decimal):
            raw[key] = str(value)
        else:
            raw[key] = value

    return raw


def build_daily_signals(
    daily_run_id: int,
    run_date,
    data_date,
    decision,
    positions: list[dict],
    stock_rows: list[dict],
):
    """Convert the sizing position list into the `strategy_daily_signal` upsert input list."""
    stock_map = {
        row["ticker_code"]: row
        for row in stock_rows
        if row.get("ticker_code")
    }

    signals = []

    for idx, position in enumerate(positions, start=1):
        ticker_code = position.get("ticker_code")
        stock = stock_map.get(ticker_code, {})

        company_name = (
            position.get("company_name")
            or stock.get("company_name")
            or ticker_code
        )

        final_score = _get(position, "score", "final_score") or _get(stock, "final_score")
        flow_score = _get(position, "flow", "flow_score") or _get(stock, "flow_score")
        tape_score = _get(position, "tape", "tape_score") or _get(stock, "tape_score")
        info_score = _get(position, "info", "info_score") or _get(stock, "info_score")
        short_score = (
            _get(position, "short", "short_score", "short_pressure_score")
            or _get(stock, "short_score", "short_pressure_score")
        )
        volatility_20d = _get(position, "vol", "volatility_20d") or _get(stock, "volatility_20d")
        intraday_range = _get(position, "intraday_range") or _get(stock, "intraday_range")
        position_size = _get(position, "position_size")

        buy_info = _build_buy_info(position, stock, decision)
        raw_features = _build_raw_features(stock)

        entry_reasons = []

        if buy_info.get("is_hot_chase"):
            entry_reasons.append("hot_chase_haircut")

        if buy_info.get("is_flow_0_9_plus_soft"):
            entry_reasons.append("flow_0_9_plus_soft_haircut")

        if buy_info.get("is_buy_day_stop_risk"):
            entry_reasons.append("buy_day_stop_risk")

        if buy_info.get("is_mid_flow_tight_range_risk"):
            entry_reasons.append("mid_flow_tight_range_risk")

        if not entry_reasons:
            entry_reasons.append("daily_buy_candidate")

        signal = {
            "daily_run_id": daily_run_id,
            "strategy_name": STRATEGY_NAME,
            "strategy_version": ENGINE_VERSION,
            "run_date": run_date,
            "data_date": data_date,
            "signal_date": run_date,
            "ticker_code": ticker_code,
            "company_name": company_name,
            "signal_type": "BUY",
            "signal_status": "READY",
            "rank_no": idx,
            "market_signal": getattr(decision, "signal_type", None),
            "base_exposure": getattr(decision, "base_exposure", None),
            "final_score": _to_decimal_or_none(final_score),
            "flow_score": _to_decimal_or_none(flow_score),
            "tape_score": _to_decimal_or_none(tape_score),
            "info_score": _to_decimal_or_none(info_score),
            "short_score": _to_decimal_or_none(short_score),
            "volatility_20d": _to_decimal_or_none(volatility_20d),
            "intraday_range": _to_decimal_or_none(intraday_range),
            "position_size": _to_decimal_or_none(position_size),
            "target_amount": None,
            "target_qty": None,
            "entry_reason": "|".join(entry_reasons),
            "block_reason": None,
            "buy_info": to_jsonb(buy_info),
            "raw_features": to_jsonb(raw_features),
            "source_table": "pre_total_stock_daily_feature",
            "processor_version": str(stock.get("processor_version") or stock.get("version") or ""),
        }

        signals.append(signal)

    return signals

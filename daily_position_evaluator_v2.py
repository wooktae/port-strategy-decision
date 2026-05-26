# C:\Workspaces\port_strategy_decision\daily_position_evaluator_v2.py

import json
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from port_strategy_common.common_sell_decision import common_evaluate_backtest_sell


PROCESSOR_VERSION = "daily_position_v2_common_sell"
DAILY_HARD_STOP_LOSS_RATE = Decimal("-0.10")


def to_decimal(value, default="0"):
    if value is None:
        return Decimal(default)

    if isinstance(value, Decimal):
        return value

    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def to_int(value, default=0):
    if value is None:
        return default

    try:
        return int(value)
    except Exception:
        return default


def json_default(value):
    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, date):
        return value.isoformat()

    return str(value)


def to_jsonb(value: Any):
    if value is None:
        return None

    return json.dumps(value, ensure_ascii=False, default=json_default)


def calc_holding_days(entry_date, decision_date):
    if entry_date is None or decision_date is None:
        return 0

    return max(0, (decision_date - entry_date).days)


def calc_expected_pnl(entry_price, current_price, qty):
    entry_price = to_decimal(entry_price)
    current_price = to_decimal(current_price)
    qty = to_decimal(qty)

    if entry_price <= 0 or qty <= 0:
        return Decimal("0"), Decimal("0")

    pnl_amount = (current_price - entry_price) * qty
    pnl_rate = (current_price / entry_price) - Decimal("1")

    return pnl_amount, pnl_rate


def normalize_market_signal(daily_run: dict, market_feature: dict):
    if daily_run and daily_run.get("market_signal"):
        return str(daily_run.get("market_signal")).upper()

    if market_feature:
        for key in (
            "market_signal",
            "signal_type",
            "market_mode",
            "decision_signal",
        ):
            value = market_feature.get(key)
            if value:
                return str(value).upper()

    return "UNKNOWN"


def get_feature_decimal(row: Optional[dict], key: str, default="0"):
    if not row:
        return Decimal(default)

    return to_decimal(row.get(key), default)


class DailySellDecisionAdapter:
    def __init__(self, signal_type: str):
        self.signal_type = signal_type


def _build_common_backtest_pos(
    position_state: dict,
    holding_days: int,
    current_cum_return: Decimal,
):
    """
    common_evaluate_backtest_sell()은 내부에서 holding_days + 1,
    prev_cum + today_ret 방식으로 계산함.

    Daily v2에서는 이미 현재 평가손익률(expected_pnl_rate)을 알고 있으므로,
    today_ret=0으로 넣고 prev_cum=current_cum_return을 넣으면
    common 내부 cum_return이 current_cum_return과 동일하게 유지됨.
    """
    return {
        "cum_return": float(current_cum_return),
        "holding_days": max(0, holding_days - 1),
        "entry_buy_info": position_state.get("entry_buy_info"),
    }


def _build_common_feature(stock_feature: dict):
    return {
        "flow_score": stock_feature.get("flow_score"),
        "final_score": stock_feature.get("final_score"),
        "short_pressure_score": stock_feature.get("short_pressure_score"),
    }


def _map_common_sell_to_daily_decision(common_result: dict):
    """
    common sell 결과를 daily_position_decision 저장 형식의 reason으로 변환.
    """
    sell_flag = bool(common_result.get("sell_flag"))
    sell_reason = common_result.get("sell_reason") or ""

    if sell_flag:
        return {
            "decision_type": "SELL",
            "decision_status": "READY",
            "sell_reason": f"SELL_{sell_reason.upper()}",
            "hold_reason": None,
            "skip_reason": None,
        }

    if sell_reason:
        hold_reason = f"HOLD_{sell_reason.upper()}"
    else:
        hold_reason = "HOLD_COMMON_NO_SELL_SIGNAL"

    return {
        "decision_type": "HOLD",
        "decision_status": "CREATED",
        "sell_reason": None,
        "hold_reason": hold_reason,
        "skip_reason": None,
    }


def _build_detail(
    *,
    decision_type,
    reason,
    common_result,
    market_signal,
    holding_days,
    expected_pnl_rate,
    expected_pnl_amount,
    flow_score,
    final_score,
    short_pressure_score,
):
    common_reason = "-"

    if isinstance(common_result, dict):
        common_reason = common_result.get("sell_reason") or "-"

    return (
        f"{decision_type}:{reason} | "
        f"common_reason={common_reason}, "
        f"market={market_signal}, "
        f"holding_days={holding_days}, "
        f"pnl_rate={expected_pnl_rate}, "
        f"pnl_amount={expected_pnl_amount}, "
        f"flow={flow_score}, "
        f"final={final_score}, "
        f"short={short_pressure_score}"
    )


def evaluate_daily_position_v2(
    *,
    daily_run: dict,
    position_state: dict,
    broker_position: Optional[dict],
    stock_feature: Optional[dict],
    market_feature: Optional[dict],
):
    """
    Daily Position v2 판단.

    목표:
    - 기존 v1은 유지
    - SELL/HOLD 판단 핵심은 common_evaluate_backtest_sell() 사용
    - 운영 제약은 Daily 계층에서 먼저 처리
      remaining_qty / broker_position / sellable_qty / price validation
    - Daily hard stop은 현재 평가손익률 기준으로 선처리
    """

    decision_date = daily_run["run_date"]
    data_date = daily_run["data_date"]

    broker_position = broker_position or {}
    stock_feature = stock_feature or {}
    market_feature = market_feature or {}

    position_state_id = position_state["id"]
    ticker_code = position_state.get("ticker_code")
    stock_name = position_state.get("stock_name")

    account_id = position_state.get("account_id")
    account_no = position_state.get("account_no")

    entry_date = position_state.get("entry_date")
    entry_price = to_decimal(position_state.get("entry_price"), "0")
    entry_qty = to_int(position_state.get("entry_qty"), 0)
    remaining_qty = to_int(position_state.get("remaining_qty"), 0)

    snapshot_qty = to_int(broker_position.get("quantity"), 0)
    sellable_qty = to_int(broker_position.get("sellable_quantity"), 0)

    current_price = (
        broker_position.get("current_price")
        or stock_feature.get("close_price")
        or entry_price
    )
    current_price = to_decimal(current_price, "0")

    holding_days = calc_holding_days(entry_date, decision_date)

    expected_qty = remaining_qty
    expected_pnl_amount, expected_pnl_rate = calc_expected_pnl(
        entry_price=entry_price,
        current_price=current_price,
        qty=expected_qty,
    )

    market_signal = normalize_market_signal(daily_run, market_feature)
    market_regime_score = get_feature_decimal(market_feature, "market_regime_score")
    breadth_pressure_score = get_feature_decimal(market_feature, "breadth_pressure_score")
    flow_pressure_score = get_feature_decimal(market_feature, "flow_pressure_score")

    flow_score = get_feature_decimal(stock_feature, "flow_score")
    info_score = get_feature_decimal(stock_feature, "info_score")
    tape_score = get_feature_decimal(stock_feature, "tape_score")
    final_score = get_feature_decimal(stock_feature, "final_score")
    short_pressure_score = get_feature_decimal(stock_feature, "short_pressure_score")
    volatility_20d = get_feature_decimal(stock_feature, "volatility_20d")
    intraday_range = get_feature_decimal(stock_feature, "intraday_range")

    validation_warnings = []

    if not broker_position:
        validation_warnings.append("NO_CONNECTOR_POSITION_SNAPSHOT")

    if snapshot_qty <= 0:
        validation_warnings.append("SNAPSHOT_QTY_ZERO_OR_MISSING")

    if remaining_qty <= 0:
        validation_warnings.append("REMAINING_QTY_ZERO_OR_MISSING")

    if sellable_qty <= 0:
        validation_warnings.append("SELLABLE_QTY_ZERO_OR_MISSING")

    if current_price <= 0:
        validation_warnings.append("CURRENT_PRICE_ZERO_OR_MISSING")

    decision_type = "HOLD"
    decision_status = "CREATED"
    sell_reason = None
    hold_reason = None
    skip_reason = None
    detail = None
    common_result = None

    # -----------------------------------------------------
    # 0. 운영 제약 검증
    # -----------------------------------------------------
    if remaining_qty <= 0:
        decision_type = "SKIP"
        decision_status = "SKIPPED"
        skip_reason = "SKIP_REMAINING_QTY_ZERO"
        detail = "전략 포지션 remaining_qty가 0 이하라서 SELL 평가 제외"

    elif snapshot_qty <= 0:
        decision_type = "SKIP"
        decision_status = "SKIPPED"
        skip_reason = "SKIP_NO_BROKER_POSITION"
        detail = "connector_position_snapshot 기준 실제 보유수량이 없어서 SELL 평가 제외"

    elif sellable_qty <= 0:
        decision_type = "HOLD"
        decision_status = "CREATED"
        hold_reason = "HOLD_NOT_SELLABLE"
        detail = "실제 매도가능수량이 0이라서 SELL 후보 생성 보류"

    elif current_price <= 0 or entry_price <= 0:
        decision_type = "SKIP"
        decision_status = "SKIPPED"
        skip_reason = "SKIP_INVALID_PRICE"
        detail = "현재가 또는 진입가가 0 이하라서 SELL 평가 제외"

    else:
        # -----------------------------------------------------
        # 1. Daily 운영 안전장치
        # common/backtest hard_stop은 raw_today_ret 기준이지만,
        # Daily Position은 현재 평가손익률 기준 손절이 필요함.
        # -----------------------------------------------------
        if expected_pnl_rate <= DAILY_HARD_STOP_LOSS_RATE:
            decision_type = "SELL"
            decision_status = "READY"
            sell_reason = "SELL_HARD_STOP"
            hold_reason = None
            skip_reason = None

            common_result = {
                "sell_flag": True,
                "sell_reason": "daily_hard_stop",
                "holding_days": holding_days,
                "cum_return": float(expected_pnl_rate),
                "flow": float(flow_score),
                "final_score": float(final_score),
                "short": float(short_pressure_score),
                "raw_today_ret": float(expected_pnl_rate),
                "today_ret": 0.0,
            }

            detail = (
                f"Daily v2 hard stop: 평가손익률 {expected_pnl_rate} "
                f"<= {DAILY_HARD_STOP_LOSS_RATE}"
            )

        # -----------------------------------------------------
        # 2. common/backtest SELL 판단
        # -----------------------------------------------------
        else:
            common_pos = _build_common_backtest_pos(
                position_state=position_state,
                holding_days=holding_days,
                current_cum_return=expected_pnl_rate,
            )
            common_feature = _build_common_feature(stock_feature)
            common_decision = DailySellDecisionAdapter(signal_type=market_signal)

            common_result = common_evaluate_backtest_sell(
                pos=common_pos,
                feature=common_feature,
                decision=common_decision,
                raw_today_ret=0.0,
                today_ret=0.0,
            )

            mapped = _map_common_sell_to_daily_decision(common_result)

            decision_type = mapped["decision_type"]
            decision_status = mapped["decision_status"]
            sell_reason = mapped["sell_reason"]
            hold_reason = mapped["hold_reason"]
            skip_reason = mapped["skip_reason"]

            reason_for_detail = sell_reason or hold_reason or skip_reason
            detail = _build_detail(
                decision_type=decision_type,
                reason=reason_for_detail,
                common_result=common_result,
                market_signal=market_signal,
                holding_days=holding_days,
                expected_pnl_rate=expected_pnl_rate,
                expected_pnl_amount=expected_pnl_amount,
                flow_score=flow_score,
                final_score=final_score,
                short_pressure_score=short_pressure_score,
            )

    order_qty = min(remaining_qty, sellable_qty)
    order_price = current_price
    target_amount = Decimal(order_qty) * order_price if order_qty > 0 else Decimal("0")

    if decision_type == "SELL" and order_qty <= 0:
        decision_type = "SKIP"
        decision_status = "SKIPPED"
        skip_reason = "SKIP_ORDER_QTY_ZERO"
        sell_reason = None
        detail = "SELL 판단이지만 order_qty가 0 이하라서 주문 후보 생성 제외"
        validation_warnings.append("SELL_ORDER_QTY_ZERO")

    reason = sell_reason or hold_reason or skip_reason

    position_context = {
        "position_state_id": position_state_id,
        "ticker_code": ticker_code,
        "stock_name": stock_name,
        "entry_date": str(entry_date) if entry_date else None,
        "entry_price": str(entry_price),
        "entry_qty": entry_qty,
        "remaining_qty": remaining_qty,
        "snapshot_qty": snapshot_qty,
        "sellable_qty": sellable_qty,
        "current_price": str(current_price),
        "holding_days": holding_days,
        "expected_pnl_amount": str(expected_pnl_amount),
        "expected_pnl_rate": str(expected_pnl_rate),
        "validation_warnings": validation_warnings,
    }

    sell_info = {
        "version": PROCESSOR_VERSION,
        "action": decision_type,
        "reason": reason,
        "detail": detail,

        "position_state_id": position_state_id,
        "ticker_code": ticker_code,
        "stock_name": stock_name,

        "entry_date": str(entry_date) if entry_date else None,
        "entry_price": str(entry_price),
        "current_price": str(current_price),
        "remaining_qty": remaining_qty,
        "snapshot_qty": snapshot_qty,
        "sellable_qty": sellable_qty,
        "holding_days": holding_days,

        "expected_pnl_rate": str(expected_pnl_rate),
        "expected_pnl_amount": str(expected_pnl_amount),

        "market_signal": market_signal,
        "market_regime_score": str(market_regime_score),
        "breadth_pressure_score": str(breadth_pressure_score),
        "flow_pressure_score": str(flow_pressure_score),

        "flow_score": str(flow_score),
        "final_score": str(final_score),
        "info_score": str(info_score),
        "tape_score": str(tape_score),
        "short_pressure_score": str(short_pressure_score),
        "volatility_20d": str(volatility_20d),
        "intraday_range": str(intraday_range),

        "order_qty": order_qty,
        "expected_sell_price": str(order_price),
        "validation_warnings": validation_warnings,

        "common_sell_result": common_result,
    }

    validation_result = {
        "source": "daily_position_evaluator_v2",
        "decision_type": decision_type,
        "decision_status": decision_status,
        "sell_reason": sell_reason,
        "hold_reason": hold_reason,
        "skip_reason": skip_reason,
        "position_state_id": position_state_id,
        "ticker_code": ticker_code,
        "stock_name": stock_name,
        "order_qty": order_qty,
        "expected_sell_price": str(order_price),
        "expected_pnl_amount": str(expected_pnl_amount),
        "expected_pnl_rate": str(expected_pnl_rate),
        "detail": detail,
        "validation_warnings": validation_warnings,
    }

    return {
        "daily_run_id": daily_run["id"],
        "strategy_name": daily_run["strategy_name"],
        "strategy_version": daily_run["strategy_version"],
        "run_date": daily_run["run_date"],
        "data_date": data_date,
        "decision_date": decision_date,

        "position_state_id": position_state_id,
        "account_id": account_id,
        "account_no": account_no,

        "ticker_code": ticker_code,
        "stock_name": stock_name,

        "decision_type": decision_type,
        "decision_status": decision_status,

        "sell_reason": sell_reason,
        "hold_reason": hold_reason,
        "skip_reason": skip_reason,

        "holding_days": holding_days,

        "entry_date": entry_date,
        "entry_price": entry_price,
        "entry_qty": entry_qty,
        "remaining_qty": remaining_qty,

        "current_price": current_price,
        "current_qty": snapshot_qty,
        "sellable_qty": sellable_qty,

        "expected_pnl_amount": expected_pnl_amount,
        "expected_pnl_rate": expected_pnl_rate,

        "market_signal": market_signal,
        "market_regime_score": market_regime_score,

        "flow_score": flow_score,
        "info_score": info_score,
        "tape_score": tape_score,
        "final_score": final_score,
        "short_pressure_score": short_pressure_score,

        "order_qty": order_qty,
        "order_price": order_price,
        "target_amount": target_amount,

        "position_context": to_jsonb(position_context),
        "sell_info": to_jsonb(sell_info),
        "validation_result": to_jsonb(validation_result),
        "raw_stock_feature": to_jsonb(stock_feature),
        "raw_market_feature": to_jsonb(market_feature),

        "source_table": "strategy_position_state",
        "processor_version": PROCESSOR_VERSION,
        "execution_order_id": None,
        "error_message": None,
    }
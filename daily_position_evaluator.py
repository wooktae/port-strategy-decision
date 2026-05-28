"""daily position HOLD/SELL/SKIP v1 판단 모듈.

기존 운영 SELL v1 기준을 daily position decision 저장 형식으로 옮긴다.
DB 업데이트나 execution order 생성은 하지 않고 decision dict만 반환한다.
"""

import json
from datetime import date
from decimal import Decimal
from typing import Any, Optional


# =========================================================
# Daily Position SELL/HOLD v1 설정값
# 기존 execution_sell_evaluator.py 운영 SELL v1과 맞춤
# =========================================================

MIN_HOLDING_DAYS_FOR_NORMAL_SELL = 2

HARD_STOP_LOSS_RATE = Decimal("-0.10")
MAX_HOLDING_DAYS = 15

MARKET_BLOCK_KEEP_PROFIT = Decimal("0.02")
QUALITY_DROP_FLOW_THRESHOLD = Decimal("0.45")
QUALITY_DROP_FINAL_THRESHOLD = Decimal("0.35")

PROFIT_POSITION_RATE = Decimal("0.03")


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


def build_detail_message(
    *,
    decision_type,
    reason,
    market_signal,
    holding_days,
    expected_pnl_rate,
    expected_pnl_amount,
    flow_score,
    final_score,
    short_pressure_score,
    validation_warnings,
):
    detail = (
        f"{decision_type}:{reason} | "
        f"market={market_signal}, "
        f"holding_days={holding_days}, "
        f"pnl_rate={expected_pnl_rate}, "
        f"pnl_amount={expected_pnl_amount}, "
        f"flow={flow_score}, "
        f"final={final_score}, "
        f"short={short_pressure_score}"
    )

    if validation_warnings:
        detail += f", warnings={validation_warnings}"

    return detail


def evaluate_daily_position(
    *,
    daily_run: dict,
    position_state: dict,
    broker_position: Optional[dict],
    stock_feature: Optional[dict],
    market_feature: Optional[dict],
):
    """
    Daily Position v1 판단.

    기존 execution_sell_evaluator.py 운영 SELL v1과 같은 판단 기준을 사용한다.
    차이점:
    - 결과를 strategy_daily_position_decision 저장용 dict로 반환한다.
    - DB 업데이트/주문 생성은 하지 않는다.
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

    # -----------------------------------------------------
    # 0. 데이터/주문 가능성 검증
    # 기존 execution_sell_evaluator.py와 맞춤
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

    # -----------------------------------------------------
    # 1. 손절은 보유일수와 무관하게 최우선
    # -----------------------------------------------------
    elif expected_pnl_rate <= HARD_STOP_LOSS_RATE:
        decision_type = "SELL"
        decision_status = "READY"
        sell_reason = "SELL_HARD_STOP"
        detail = f"평가손익률 {expected_pnl_rate} <= hard stop {HARD_STOP_LOSS_RATE}"

    # -----------------------------------------------------
    # 2. 최소 보유일수 보호
    # -----------------------------------------------------
    elif holding_days < MIN_HOLDING_DAYS_FOR_NORMAL_SELL:
        decision_type = "HOLD"
        decision_status = "CREATED"
        hold_reason = "HOLD_MIN_HOLDING_DAYS"
        detail = (
            f"보유일수 {holding_days}일 < "
            f"최소 일반 매도일수 {MIN_HOLDING_DAYS_FOR_NORMAL_SELL}일"
        )

    # -----------------------------------------------------
    # 3. 최대 보유일수
    # -----------------------------------------------------
    elif holding_days >= MAX_HOLDING_DAYS:
        decision_type = "SELL"
        decision_status = "READY"
        sell_reason = "SELL_MAX_HOLDING_DAYS"
        detail = f"보유일수 {holding_days}일 >= 최대 보유일수 {MAX_HOLDING_DAYS}일"

    # -----------------------------------------------------
    # 4. 시장 BLOCK 조건
    # -----------------------------------------------------
    elif market_signal == "BLOCK" and expected_pnl_rate < MARKET_BLOCK_KEEP_PROFIT:
        decision_type = "SELL"
        decision_status = "READY"
        sell_reason = "SELL_MARKET_BLOCK_WEAK_PROFIT"
        detail = (
            f"market_signal=BLOCK이고 평가손익률 {expected_pnl_rate} "
            f"< keep_profit {MARKET_BLOCK_KEEP_PROFIT}"
        )

    # -----------------------------------------------------
    # 5. 품질 저하
    # -----------------------------------------------------
    elif (
        flow_score < QUALITY_DROP_FLOW_THRESHOLD
        and final_score < QUALITY_DROP_FINAL_THRESHOLD
    ):
        decision_type = "SELL"
        decision_status = "READY"
        sell_reason = "SELL_QUALITY_DROP"
        detail = (
            f"flow_score {flow_score} < {QUALITY_DROP_FLOW_THRESHOLD}, "
            f"final_score {final_score} < {QUALITY_DROP_FINAL_THRESHOLD}"
        )

    # -----------------------------------------------------
    # 6. 수익권 포지션은 기본 보유
    # -----------------------------------------------------
    elif expected_pnl_rate >= PROFIT_POSITION_RATE:
        decision_type = "HOLD"
        decision_status = "CREATED"
        hold_reason = "HOLD_PROFIT_POSITION"
        detail = f"평가손익률 {expected_pnl_rate} >= 수익권 기준 {PROFIT_POSITION_RATE}"

        if short_pressure_score >= Decimal("0.80"):
            detail += f" / short_pressure_score 높음: {short_pressure_score}"

    # -----------------------------------------------------
    # 7. 기본 HOLD
    # -----------------------------------------------------
    else:
        decision_type = "HOLD"
        decision_status = "CREATED"
        hold_reason = "HOLD_DEFAULT"
        detail = (
            f"기본 HOLD: pnl_rate={expected_pnl_rate}, "
            f"pnl_amount={expected_pnl_amount}, "
            f"flow={flow_score}, final={final_score}, "
            f"market_signal={market_signal}"
        )

        if short_pressure_score >= Decimal("0.80"):
            detail += f", short_pressure_score 높음: {short_pressure_score}"

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

    if detail is None:
        detail = build_detail_message(
            decision_type=decision_type,
            reason=reason,
            market_signal=market_signal,
            holding_days=holding_days,
            expected_pnl_rate=expected_pnl_rate,
            expected_pnl_amount=expected_pnl_amount,
            flow_score=flow_score,
            final_score=final_score,
            short_pressure_score=short_pressure_score,
            validation_warnings=validation_warnings,
        )

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
        "version": "daily_position_v1",
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
        "rules": {
            "min_holding_days_for_normal_sell": MIN_HOLDING_DAYS_FOR_NORMAL_SELL,
            "hard_stop_loss_rate": str(HARD_STOP_LOSS_RATE),
            "max_holding_days": MAX_HOLDING_DAYS,
            "market_block_keep_profit": str(MARKET_BLOCK_KEEP_PROFIT),
            "quality_drop_flow_threshold": str(QUALITY_DROP_FLOW_THRESHOLD),
            "quality_drop_final_threshold": str(QUALITY_DROP_FINAL_THRESHOLD),
            "profit_position_rate": str(PROFIT_POSITION_RATE),
        },
    }

    validation_result = {
        "source": "daily_position_evaluator",
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
        "processor_version": str(
            stock_feature.get("processor_version")
            or market_feature.get("processor_version")
            or ""
        ),
        "execution_order_id": None,
        "error_message": None,
    }

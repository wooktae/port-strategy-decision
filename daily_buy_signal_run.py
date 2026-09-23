"""daily BUY signal generation entrypoint.

Reads the preprocessing total features and performs market/filter/sizing,
BUY signal persistence, and BLOCK watch persistence. The default operational
mode performs DB writes and run status updates. The --shadow mode uses the same
inputs and calculation path but only prints the results as JSON within a
read-only transaction.
"""

import argparse
import json
import traceback
from decimal import Decimal

import psycopg2
from port_strategy_common.common_buy_guard import common_decide_buy_guard
from port_strategy_common.common_buy_sizing import (
    common_apply_backtest_buy_size_haircut,
)
from port_strategy_common.common_context import CommonStockContext
from port_strategy_common.common_result import CommonMarketDecision
from port_strategy_common.common_utils import common_safe_float

from port_strategy_decision.backtest_filter import filter_buy_candidates
from port_strategy_decision.backtest_market import evaluate_market
from port_strategy_decision.backtest_sizing import allocate_positions
from port_strategy_decision.daily_block_watch_builder import (
    build_block_watch_candidates,
)
from port_strategy_decision.daily_block_watch_repository import (
    delete_block_watch_candidates,
    insert_block_watch_candidates,
)
from port_strategy_decision.daily_feature_loader import load_daily_features
from port_strategy_decision.daily_repository import (
    create_or_replace_daily_run,
    insert_daily_signals,
    update_daily_run_failed,
    update_daily_run_success,
)
from port_strategy_decision.daily_signal_builder import build_daily_signals
from port_strategy_decision.db_config import get_db_config

SHADOW_DAILY_RUN_ID = 0
SHADOW_MODE = "SHADOW"
SHADOW_BUY_SUMMARY_EVENT = "DECISION_SHADOW_BUY_SUMMARY"
SHADOW_BUY_SIGNAL_EVENT = "DECISION_SHADOW_BUY_SIGNAL"
SHADOW_BLOCK_WATCH_EVENT = "DECISION_SHADOW_BLOCK_WATCH"


def get_conn():
    return psycopg2.connect(**get_db_config())


def _json_default(value):
    return str(value)


def _print_json_event(event: str, payload: dict):
    print(
        json.dumps(
            {
                "event": event,
                **payload,
            },
            ensure_ascii=False,
            default=_json_default,
            sort_keys=True,
        )
    )


def _to_common_market_decision(decision) -> CommonMarketDecision:
    return CommonMarketDecision(
        market_signal=str(decision.signal_type),
        base_exposure=float(decision.base_exposure),
        max_positions=int(decision.max_positions),
        min_score=float(decision.min_score),
        min_flow=float(decision.min_flow),
        reason=str(decision.reason),
        detail={},
    )


def _to_common_stock_context(position: dict, run_date) -> CommonStockContext:
    return CommonStockContext(
        trade_date=str(run_date),
        ticker_code=str(position.get("ticker_code", "")),
        ticker_name=position.get("company_name") or position.get("stock_name"),
        final_score=common_safe_float(position.get("final_score"), 0.0),
        flow_pressure_score=common_safe_float(position.get("flow_score"), 0.0),
        tape_score=common_safe_float(position.get("tape_score"), 0.0),
        short_pressure_score=common_safe_float(
            position.get("short_pressure_score"),
            0.0,
        ),
        volatility_score=common_safe_float(position.get("volatility_20d"), 0.0),
        intraday_range=common_safe_float(position.get("intraday_range"), 0.0),
        raw=dict(position),
    )


def apply_daily_buy_toxic_haircut(
    positions: list[dict],
    decision,
    run_date,
) -> list[dict]:
    """Apply the shared buy guard/haircut results to the position dict for daily signal storage."""
    common_market_decision = _to_common_market_decision(decision)
    enriched = []

    for position in positions:
        stock_context = _to_common_stock_context(position, run_date)

        guard = common_decide_buy_guard(
            stock=stock_context,
            market=common_market_decision,
            config={},
        )

        original_size = common_safe_float(position.get("position_size"), 0.0)

        adjusted_size, haircut_info = common_apply_backtest_buy_size_haircut(
            size=original_size,
            guard=guard,
            config={},
        )

        risk_flags = guard.detail.get("risk_flags", {})

        enriched_position = {
            **position,
            "position_size": Decimal(str(adjusted_size)),
            "is_hot_chase": bool(
                risk_flags.get(
                    "is_hot_chase",
                    risk_flags.get("hot_chase", False),
                )
            ),
            "is_buy_day_stop_risk": bool(
                risk_flags.get(
                    "is_buy_day_stop_risk",
                    risk_flags.get("buy_day_stop_risk", False),
                )
            ),
            "is_mid_flow_tight_range_risk": bool(
                risk_flags.get(
                    "is_mid_flow_tight_range_risk",
                    risk_flags.get("mid_flow_tight_range_risk", False),
                )
            ),
            "is_flow_0_9_plus_soft": bool(
                risk_flags.get(
                    "is_flow_0_9_plus_soft",
                    risk_flags.get("flow_0_9_plus_soft", False),
                )
            ),
            "size_haircut_reason": haircut_info.get("applied_reason"),
            "size_haircut_multiplier": haircut_info.get("multiplier"),
            "size_before_haircut": Decimal(
                str(haircut_info.get("original_size", original_size))
            ),
            "size_after_haircut": Decimal(
                str(haircut_info.get("adjusted_size", adjusted_size))
            ),
        }

        enriched.append(enriched_position)

    return enriched


def _calculate_daily_signal(
    *,
    conn,
    run_date=None,
    data_date=None,
    daily_run_id: int,
):
    """BUY decision calculation path shared by the operational and Shadow modes."""
    features = load_daily_features(
        conn=conn,
        run_date=run_date,
        data_date=data_date,
    )

    resolved_run_date = features["run_date"]
    resolved_data_date = features["data_date"]
    market = features["market"]
    stocks = features["stocks"]

    decision = evaluate_market(market)
    candidates = filter_buy_candidates(stocks, decision)
    positions = allocate_positions(candidates, decision)

    signals = build_daily_signals(
        daily_run_id=daily_run_id,
        run_date=resolved_run_date,
        data_date=resolved_data_date,
        decision=decision,
        positions=positions,
        stock_rows=stocks,
    )

    block_watch_candidates = build_block_watch_candidates(
        daily_run_id=daily_run_id,
        run_date=resolved_run_date,
        data_date=resolved_data_date,
        market_signal=str(decision.signal_type),
        stock_candidates=stocks,
    )

    return {
        "run_date": resolved_run_date,
        "data_date": resolved_data_date,
        "decision": decision,
        "stocks": stocks,
        "candidates": candidates,
        "positions": positions,
        "signals": signals,
        "block_watch_candidates": block_watch_candidates,
    }


def run_daily_signal(run_date=None, data_date=None, run_note=None):
    """Create a daily run and persist the BUY signals and BLOCK watch candidates to the DB."""
    conn = get_conn()
    daily_run_id = None

    try:
        features = load_daily_features(
            conn=conn,
            run_date=run_date,
            data_date=data_date,
        )

        resolved_run_date = features["run_date"]
        resolved_data_date = features["data_date"]
        market = features["market"]
        stocks = features["stocks"]

        daily_run_id = create_or_replace_daily_run(
            conn=conn,
            run_date=resolved_run_date,
            data_date=resolved_data_date,
            run_type="DAILY_SIGNAL",
            run_note=run_note or "daily buy signal generation",
        )

        decision = evaluate_market(market)
        candidates = filter_buy_candidates(stocks, decision)
        positions = allocate_positions(candidates, decision)

        signals = build_daily_signals(
            daily_run_id=daily_run_id,
            run_date=resolved_run_date,
            data_date=resolved_data_date,
            decision=decision,
            positions=positions,
            stock_rows=stocks,
        )

        signal_ids = insert_daily_signals(conn, signals)

        delete_block_watch_candidates(conn, daily_run_id)

        block_watch_candidates = build_block_watch_candidates(
            daily_run_id=daily_run_id,
            run_date=resolved_run_date,
            data_date=resolved_data_date,
            market_signal=str(decision.signal_type),
            stock_candidates=stocks,
        )

        block_watch_count = insert_block_watch_candidates(
            conn,
            block_watch_candidates,
        )

        update_daily_run_success(
            conn=conn,
            daily_run_id=daily_run_id,
            decision=decision,
            candidate_count=len(candidates),
            signal_count=len(signals),
        )

        conn.commit()

        print("===== DAILY SIGNAL RESULT =====")
        print("daily_run_id:", daily_run_id)
        print("run_date:", resolved_run_date)
        print("data_date:", resolved_data_date)
        print("market_signal:", decision.signal_type)
        print("base_exposure:", decision.base_exposure)
        print("max_positions:", decision.max_positions)
        print("candidates:", len(candidates))
        print("signals:", len(signals))
        print("block_watch:", block_watch_count)

        for signal in signals[:10]:
            print(
                signal["rank_no"],
                signal["ticker_code"],
                signal["company_name"],
                "score=",
                signal["final_score"],
                "flow=",
                signal["flow_score"],
                "size=",
                signal["position_size"],
            )

        return {
            "daily_run_id": daily_run_id,
            "run_date": resolved_run_date,
            "data_date": resolved_data_date,
            "decision": decision,
            "candidate_count": len(candidates),
            "signal_count": len(signals),
            "signal_ids": signal_ids,
            "block_watch_count": block_watch_count,
        }

    except Exception as exc:
        conn.rollback()

        if daily_run_id is not None:
            try:
                update_daily_run_failed(
                    conn=conn,
                    daily_run_id=daily_run_id,
                    error_message=str(exc),
                )
                conn.commit()
            except Exception:
                conn.rollback()

        print("===== DAILY SIGNAL FAILED =====")
        print(str(exc))
        traceback.print_exc()
        raise

    finally:
        conn.close()


def run_daily_signal_shadow(run_date=None, data_date=None):
    """Print the BUY/BLOCK Watch decision results as JSON without modifying the operational DB."""
    conn = get_conn()

    try:
        conn.set_session(readonly=True, autocommit=False)

        result = _calculate_daily_signal(
            conn=conn,
            run_date=run_date,
            data_date=data_date,
            daily_run_id=SHADOW_DAILY_RUN_ID,
        )

        decision = result["decision"]
        signals = result["signals"]
        block_watch_candidates = result["block_watch_candidates"]

        seen_tickers = set()

        for signal in signals:
            ticker_code = signal.get("ticker_code")

            if not ticker_code:
                raise RuntimeError("Shadow BUY signal ticker_code is required.")

            if ticker_code in seen_tickers:
                raise RuntimeError(
                    f"Duplicate Shadow BUY ticker_code detected: {ticker_code}"
                )

            seen_tickers.add(ticker_code)

            _print_json_event(
                SHADOW_BUY_SIGNAL_EVENT,
                {
                    "mode": SHADOW_MODE,
                    "run_date": result["run_date"],
                    "data_date": result["data_date"],
                    "rank_no": signal.get("rank_no"),
                    "ticker_code": ticker_code,
                    "company_name": signal.get("company_name"),
                    "market_signal": signal.get("market_signal"),
                    "final_score": signal.get("final_score"),
                    "flow_score": signal.get("flow_score"),
                    "position_size": signal.get("position_size"),
                    "target_qty": signal.get("target_qty"),
                    "entry_reason": signal.get("entry_reason"),
                    "processor_version": signal.get("processor_version"),
                    "write_count": 0,
                },
            )

        for candidate in block_watch_candidates:
            _print_json_event(
                SHADOW_BLOCK_WATCH_EVENT,
                {
                    "mode": SHADOW_MODE,
                    "run_date": result["run_date"],
                    "data_date": result["data_date"],
                    "ticker_code": candidate.get("ticker_code"),
                    "stock_name": candidate.get("stock_name"),
                    "market_signal": candidate.get("market_signal"),
                    "watch_status": candidate.get("watch_status"),
                    "watch_reason": candidate.get("watch_reason"),
                    "final_score": candidate.get("final_score"),
                    "flow_score": candidate.get("flow_score"),
                    "write_count": 0,
                },
            )

        summary = {
            "mode": SHADOW_MODE,
            "run_date": result["run_date"],
            "data_date": result["data_date"],
            "market_signal": getattr(decision, "signal_type", None),
            "base_exposure": getattr(decision, "base_exposure", None),
            "max_positions": getattr(decision, "max_positions", None),
            "min_score": getattr(decision, "min_score", None),
            "candidate_count": len(result["candidates"]),
            "signal_count": len(signals),
            "block_watch_count": len(block_watch_candidates),
            "write_count": 0,
            "source": "pre_total_market_daily_feature,pre_total_stock_daily_feature",
        }

        _print_json_event(SHADOW_BUY_SUMMARY_EVENT, summary)
        return summary

    except Exception:
        conn.rollback()
        print("===== DAILY SIGNAL SHADOW FAILED =====")
        traceback.print_exc()
        raise

    finally:
        conn.rollback()
        conn.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run daily strategy signal generation."
    )
    parser.add_argument(
        "--run-date",
        required=False,
        help="Run date. Example: 2026-05-07",
    )
    parser.add_argument(
        "--data-date",
        required=False,
        help="Feature data date. Example: 2026-05-06",
    )
    parser.add_argument("--note", required=False, help="Run note")
    parser.add_argument(
        "--shadow",
        action="store_true",
        help="Run read-only Shadow Canary and print JSON results without DB writes.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.shadow:
        run_daily_signal_shadow(
            run_date=args.run_date,
            data_date=args.data_date,
        )
    else:
        run_daily_signal(
            run_date=args.run_date,
            data_date=args.data_date,
            run_note=args.note,
        )

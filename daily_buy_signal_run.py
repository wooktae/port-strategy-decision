import argparse
import traceback

import psycopg2

from port_strategy_decision.backtest_market import evaluate_market
from port_strategy_decision.backtest_filter import filter_buy_candidates
from port_strategy_decision.backtest_sizing import allocate_positions
from port_strategy_decision.db_config import get_db_config
from port_strategy_decision.daily_feature_loader import load_daily_features
from port_strategy_decision.daily_repository import (
    create_or_replace_daily_run,
    insert_daily_signals,
    update_daily_run_success,
    update_daily_run_failed,
)
from port_strategy_decision.daily_signal_builder import build_daily_signals

from decimal import Decimal

from port_strategy_common.common_context import CommonStockContext
from port_strategy_common.common_result import CommonMarketDecision
from port_strategy_common.common_buy_guard import common_decide_buy_guard
from port_strategy_common.common_buy_sizing import common_apply_backtest_buy_size_haircut
from port_strategy_common.common_utils import common_safe_float

from port_strategy_decision.daily_block_watch_builder import build_block_watch_candidates
from port_strategy_decision.daily_block_watch_repository import (
    delete_block_watch_candidates,
    insert_block_watch_candidates,
)


def get_conn():
    return psycopg2.connect(**get_db_config())

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
        short_pressure_score=common_safe_float(position.get("short_pressure_score"), 0.0),
        volatility_score=common_safe_float(position.get("volatility_20d"), 0.0),
        intraday_range=common_safe_float(position.get("intraday_range"), 0.0),
        raw=dict(position),
    )


def apply_daily_buy_toxic_haircut(positions: list[dict], decision, run_date) -> list[dict]:
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
                risk_flags.get("is_hot_chase", risk_flags.get("hot_chase", False))
            ),
            "is_buy_day_stop_risk": bool(
                risk_flags.get("is_buy_day_stop_risk", risk_flags.get("buy_day_stop_risk", False))
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
            "size_before_haircut": Decimal(str(haircut_info.get("original_size", original_size))),
            "size_after_haircut": Decimal(str(haircut_info.get("adjusted_size", adjusted_size))),
        }

        enriched.append(enriched_position)

    return enriched

def run_daily_signal(run_date=None, data_date=None, run_note=None):
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

    except Exception as e:
        conn.rollback()

        if daily_run_id is not None:
            try:
                update_daily_run_failed(
                    conn=conn,
                    daily_run_id=daily_run_id,
                    error_message=str(e),
                )
                conn.commit()
            except Exception:
                conn.rollback()

        print("===== DAILY SIGNAL FAILED =====")
        print(str(e))
        traceback.print_exc()
        raise

    finally:
        conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Run daily strategy signal generation.")
    parser.add_argument("--run-date", required=False, help="Run date. Example: 2026-05-07")
    parser.add_argument("--data-date", required=False, help="Feature data date. Example: 2026-05-06")
    parser.add_argument("--note", required=False, help="Run note")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    run_daily_signal(
        run_date=args.run_date,
        data_date=args.data_date,
        run_note=args.note,
    )

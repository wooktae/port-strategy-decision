"""daily position HOLD/SELL/SKIP decision generation entrypoint.

Reads the latest completed daily run and the active positions and evaluates them
with the v1/v2 evaluator. The default operational mode persists the results to
the DB and updates the position state latest evaluation values. The --shadow
mode uses the same inputs and evaluator but only prints the results as JSON
within a read-only transaction.
"""

import argparse
import json
import traceback

from port_strategy_decision.daily_position_evaluator import evaluate_daily_position
from port_strategy_decision.daily_position_evaluator_v2 import (
    evaluate_daily_position_v2,
)
from port_strategy_decision.daily_position_repository import (
    get_active_position_states,
    get_conn,
    get_daily_position_decisions,
    get_latest_broker_position,
    get_latest_daily_run,
    get_market_feature,
    get_stock_feature,
    update_position_state_latest_evaluation,
    upsert_daily_position_decision,
)

DEFAULT_EVALUATOR_VERSION = "v1"
SUPPORTED_EVALUATOR_VERSIONS = {"v1", "v2"}
ALLOWED_DECISION_TYPES = {"HOLD", "SELL", "SKIP"}

SHADOW_MODE = "SHADOW"
SHADOW_POSITION_SUMMARY_EVENT = "DECISION_SHADOW_POSITION_SUMMARY"
SHADOW_POSITION_DECISION_EVENT = "DECISION_SHADOW_POSITION_DECISION"


def print_header(title):
    print()
    print("========================================")
    print(title)
    print("========================================")


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


def normalize_evaluator_version(evaluator_version=None):
    version = (evaluator_version or DEFAULT_EVALUATOR_VERSION).lower().strip()

    if version not in SUPPORTED_EVALUATOR_VERSIONS:
        raise ValueError(
            f"Unsupported evaluator_version={evaluator_version}. "
            f"Supported values: {sorted(SUPPORTED_EVALUATOR_VERSIONS)}"
        )

    return version


def evaluate_position_by_version(
    *,
    evaluator_version,
    daily_run,
    position_state,
    broker_position,
    stock_feature,
    market_feature,
):
    if evaluator_version == "v2":
        return evaluate_daily_position_v2(
            daily_run=daily_run,
            position_state=position_state,
            broker_position=broker_position,
            stock_feature=stock_feature,
            market_feature=market_feature,
        )

    return evaluate_daily_position(
        daily_run=daily_run,
        position_state=position_state,
        broker_position=broker_position,
        stock_feature=stock_feature,
        market_feature=market_feature,
    )


def _get_decision_reason(decision: dict):
    return (
        decision.get("sell_reason")
        or decision.get("hold_reason")
        or decision.get("skip_reason")
    )


def _validate_shadow_decision(decision: dict, seen_position_ids: set):
    decision_type = str(decision.get("decision_type") or "").upper()
    position_state_id = decision.get("position_state_id")

    if decision_type not in ALLOWED_DECISION_TYPES:
        raise RuntimeError(
            f"Unsupported Shadow decision_type={decision_type!r} "
            f"for position_state_id={position_state_id}"
        )

    if position_state_id is None:
        raise RuntimeError("Shadow position_state_id is required.")

    if position_state_id in seen_position_ids:
        raise RuntimeError(
            f"Duplicate Shadow position_state_id detected: {position_state_id}"
        )

    reason = _get_decision_reason(decision)

    if not reason:
        raise RuntimeError(
            f"Shadow reason is required for position_state_id={position_state_id}"
        )

    if decision_type == "SELL" and not decision.get("sell_reason"):
        raise RuntimeError(
            f"SELL requires sell_reason for position_state_id={position_state_id}"
        )

    if decision_type == "HOLD" and not decision.get("hold_reason"):
        raise RuntimeError(
            f"HOLD requires hold_reason for position_state_id={position_state_id}"
        )

    if decision_type == "SKIP" and not decision.get("skip_reason"):
        raise RuntimeError(
            f"SKIP requires skip_reason for position_state_id={position_state_id}"
        )

    seen_position_ids.add(position_state_id)
    return reason


def run_daily_position_decision(account_no=None, evaluator_version=None):
    """Generate and persist a daily position decision for each active position."""
    evaluator_version = normalize_evaluator_version(evaluator_version)

    conn = get_conn()
    conn.autocommit = False

    try:
        daily_run = get_latest_daily_run(conn)

        position_states = get_active_position_states(
            conn=conn,
            account_no=account_no,
        )

        market_feature = get_market_feature(
            conn=conn,
            data_date=daily_run["data_date"],
        )

        result_summary = {
            "daily_run_id": daily_run["id"],
            "run_date": daily_run["run_date"],
            "data_date": daily_run["data_date"],
            "market_signal": daily_run["market_signal"],
            "evaluator_version": evaluator_version,
            "position_count": len(position_states),
            "decision_count": 0,
            "sell_count": 0,
            "hold_count": 0,
            "skip_count": 0,
            "decision_ids": [],
        }

        print_header("[Daily Position Decision Run]")
        print(f"daily_run_id      : {daily_run['id']}")
        print(f"run_date          : {daily_run['run_date']}")
        print(f"data_date         : {daily_run['data_date']}")
        print(f"market_signal     : {daily_run['market_signal']}")
        print(f"evaluator_version : {evaluator_version}")
        print(f"positions         : {len(position_states)}")

        for position_state in position_states:
            ticker_code = position_state["ticker_code"]

            broker_position = get_latest_broker_position(
                conn=conn,
                account_id=position_state["account_id"],
                ticker_code=ticker_code,
            )

            stock_feature = get_stock_feature(
                conn=conn,
                ticker_code=ticker_code,
                data_date=daily_run["data_date"],
            )

            decision = evaluate_position_by_version(
                evaluator_version=evaluator_version,
                daily_run=daily_run,
                position_state=position_state,
                broker_position=broker_position,
                stock_feature=stock_feature,
                market_feature=market_feature,
            )

            decision_id = upsert_daily_position_decision(
                conn=conn,
                decision=decision,
            )

            update_position_state_latest_evaluation(
                conn=conn,
                decision=decision,
            )

            result_summary["decision_count"] += 1
            result_summary["decision_ids"].append(decision_id)

            decision_type = decision["decision_type"]

            if decision_type == "SELL":
                result_summary["sell_count"] += 1
            elif decision_type == "HOLD":
                result_summary["hold_count"] += 1
            elif decision_type == "SKIP":
                result_summary["skip_count"] += 1

            reason = _get_decision_reason(decision) or "-"

            print(
                f"- #{decision_id} "
                f"{decision['ticker_code']} {decision['stock_name']} | "
                f"{decision['decision_type']} | "
                f"{reason} | "
                f"qty={decision['remaining_qty']} "
                f"sellable={decision['sellable_qty']} "
                f"price={decision['current_price']} "
                f"pnl={decision['expected_pnl_rate']}"
            )

        conn.commit()

        print_header("[Daily Position Decision Summary]")
        print(f"daily_run_id       : {result_summary['daily_run_id']}")
        print(f"evaluator_version  : {result_summary['evaluator_version']}")
        print(f"decision_count     : {result_summary['decision_count']}")
        print(f"sell_count         : {result_summary['sell_count']}")
        print(f"hold_count         : {result_summary['hold_count']}")
        print(f"skip_count         : {result_summary['skip_count']}")
        print(f"decision_ids       : {result_summary['decision_ids']}")

        return result_summary

    except Exception as exc:
        conn.rollback()

        print_header("[ERROR]")
        print(str(exc))
        traceback.print_exc()
        raise

    finally:
        conn.close()


def run_daily_position_decision_shadow(
    account_no=None,
    evaluator_version=None,
):
    """Print the position decision results as JSON without modifying the operational DB."""
    evaluator_version = normalize_evaluator_version(evaluator_version)

    conn = get_conn()

    try:
        conn.set_session(readonly=True, autocommit=False)

        daily_run = get_latest_daily_run(conn)

        position_states = get_active_position_states(
            conn=conn,
            account_no=account_no,
        )

        market_feature = get_market_feature(
            conn=conn,
            data_date=daily_run["data_date"],
        )

        summary = {
            "mode": SHADOW_MODE,
            "daily_run_id": daily_run["id"],
            "run_date": daily_run["run_date"],
            "data_date": daily_run["data_date"],
            "market_signal": daily_run["market_signal"],
            "evaluator_version": evaluator_version,
            "position_count": len(position_states),
            "decision_count": 0,
            "sell_count": 0,
            "hold_count": 0,
            "skip_count": 0,
            "write_count": 0,
            "source": (
                "strategy_daily_run,strategy_position_state,"
                "connector_position_snapshot,pre_total_stock_daily_feature,"
                "pre_total_market_daily_feature"
            ),
        }

        seen_position_ids = set()

        for position_state in position_states:
            ticker_code = position_state["ticker_code"]

            broker_position = get_latest_broker_position(
                conn=conn,
                account_id=position_state["account_id"],
                ticker_code=ticker_code,
            )

            stock_feature = get_stock_feature(
                conn=conn,
                ticker_code=ticker_code,
                data_date=daily_run["data_date"],
            )

            decision = evaluate_position_by_version(
                evaluator_version=evaluator_version,
                daily_run=daily_run,
                position_state=position_state,
                broker_position=broker_position,
                stock_feature=stock_feature,
                market_feature=market_feature,
            )

            reason = _validate_shadow_decision(
                decision=decision,
                seen_position_ids=seen_position_ids,
            )

            decision_type = decision["decision_type"]

            summary["decision_count"] += 1
            summary[f"{decision_type.lower()}_count"] += 1

            _print_json_event(
                SHADOW_POSITION_DECISION_EVENT,
                {
                    "mode": SHADOW_MODE,
                    "daily_run_id": daily_run["id"],
                    "run_date": daily_run["run_date"],
                    "data_date": daily_run["data_date"],
                    "evaluator_version": evaluator_version,
                    "position_state_id": decision.get("position_state_id"),
                    "ticker_code": decision.get("ticker_code"),
                    "stock_name": decision.get("stock_name"),
                    "decision_type": decision_type,
                    "decision_status": decision.get("decision_status"),
                    "reason": reason,
                    "holding_days": decision.get("holding_days"),
                    "remaining_qty": decision.get("remaining_qty"),
                    "current_qty": decision.get("current_qty"),
                    "sellable_qty": decision.get("sellable_qty"),
                    "current_price": decision.get("current_price"),
                    "expected_pnl_rate": decision.get("expected_pnl_rate"),
                    "order_qty": decision.get("order_qty"),
                    "processor_version": decision.get("processor_version"),
                    "write_count": 0,
                },
            )

        _print_json_event(SHADOW_POSITION_SUMMARY_EVENT, summary)
        return summary

    except Exception:
        conn.rollback()
        print_header("[Daily Position Shadow ERROR]")
        traceback.print_exc()
        raise

    finally:
        conn.rollback()
        conn.close()


def validate_latest_daily_position_decisions():
    """Query the position decisions of the latest daily run and print them to the console."""
    conn = get_conn()

    try:
        daily_run = get_latest_daily_run(conn)
        decisions = get_daily_position_decisions(conn, daily_run["id"])

        print_header("[Latest Daily Position Decisions]")
        print(f"daily_run_id : {daily_run['id']}")
        print(f"count        : {len(decisions)}")

        for decision in decisions:
            reason = (
                decision["sell_reason"]
                or decision["hold_reason"]
                or decision["skip_reason"]
                or "-"
            )
            print(
                f"- #{decision['id']} "
                f"{decision['ticker_code']} {decision['stock_name']} | "
                f"{decision['decision_type']} / "
                f"{decision['decision_status']} | "
                f"{reason} | "
                f"qty={decision['remaining_qty']} "
                f"sellable={decision['sellable_qty']} "
                f"price={decision['current_price']} "
                f"pnl={decision['expected_pnl_rate']}"
            )

        return decisions

    finally:
        conn.close()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run daily position HOLD/SELL decision."
    )
    parser.add_argument(
        "--account-no",
        required=False,
        help="Account no filter. Example: 50162203",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only print latest decisions.",
    )
    parser.add_argument(
        "--shadow",
        action="store_true",
        help="Run read-only Shadow Canary and print JSON results without DB writes.",
    )
    parser.add_argument(
        "--evaluator-version",
        required=False,
        default=DEFAULT_EVALUATOR_VERSION,
        choices=sorted(SUPPORTED_EVALUATOR_VERSIONS),
        help="Daily position evaluator version. Default: v1",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.shadow and args.validate_only:
        raise SystemExit("--shadow and --validate-only cannot be used together.")

    if args.validate_only:
        validate_latest_daily_position_decisions()
    elif args.shadow:
        run_daily_position_decision_shadow(
            account_no=args.account_no,
            evaluator_version=args.evaluator_version,
        )
    else:
        run_daily_position_decision(
            account_no=args.account_no,
            evaluator_version=args.evaluator_version,
        )

"""daily position HOLD/SELL/SKIP decision 생성 entrypoint.

최신 완료 daily run과 활성 포지션을 읽어 v1/v2 evaluator로 판단하고 DB에 저장한다.
position state latest 평가 갱신이 포함되므로 운영 승인 없는 정리 작업 중에는 실행하지 않는다.
"""

import argparse
import traceback

from port_strategy_decision.daily_position_evaluator import evaluate_daily_position
from port_strategy_decision.daily_position_evaluator_v2 import evaluate_daily_position_v2
from port_strategy_decision.daily_position_repository import (
    get_conn,
    get_latest_daily_run,
    get_active_position_states,
    get_latest_broker_position,
    get_stock_feature,
    get_market_feature,
    upsert_daily_position_decision,
    update_position_state_latest_evaluation,
    get_daily_position_decisions,
)


DEFAULT_EVALUATOR_VERSION = "v1"
SUPPORTED_EVALUATOR_VERSIONS = {"v1", "v2"}


def print_header(title):
    print()
    print("========================================")
    print(title)
    print("========================================")


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


def run_daily_position_decision(account_no=None, evaluator_version=None):
    """활성 포지션별 daily position decision을 생성하고 저장한다."""
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

        for ps in position_states:
            ticker_code = ps["ticker_code"]

            broker_position = get_latest_broker_position(
                conn=conn,
                account_id=ps["account_id"],
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
                position_state=ps,
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

            reason = (
                decision.get("sell_reason")
                or decision.get("hold_reason")
                or decision.get("skip_reason")
                or "-"
            )

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

    except Exception as e:
        conn.rollback()

        print_header("[ERROR]")
        print(str(e))
        traceback.print_exc()
        raise

    finally:
        conn.close()


def validate_latest_daily_position_decisions():
    """최신 daily run의 position decision을 조회해 콘솔에 출력한다."""
    conn = get_conn()

    try:
        daily_run = get_latest_daily_run(conn)
        decisions = get_daily_position_decisions(conn, daily_run["id"])

        print_header("[Latest Daily Position Decisions]")
        print(f"daily_run_id : {daily_run['id']}")
        print(f"count        : {len(decisions)}")

        for d in decisions:
            reason = d["sell_reason"] or d["hold_reason"] or d["skip_reason"] or "-"
            print(
                f"- #{d['id']} "
                f"{d['ticker_code']} {d['stock_name']} | "
                f"{d['decision_type']} / {d['decision_status']} | "
                f"{reason} | "
                f"qty={d['remaining_qty']} "
                f"sellable={d['sellable_qty']} "
                f"price={d['current_price']} "
                f"pnl={d['expected_pnl_rate']}"
            )

        return decisions

    finally:
        conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Run daily position HOLD/SELL decision.")
    parser.add_argument("--account-no", required=False, help="Account no filter. Example: 50162203")
    parser.add_argument("--validate-only", action="store_true", help="Only print latest decisions.")
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

    if args.validate_only:
        validate_latest_daily_position_decisions()
    else:
        run_daily_position_decision(
            account_no=args.account_no,
            evaluator_version=args.evaluator_version,
        )

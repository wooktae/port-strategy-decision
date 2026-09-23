"""
Decision Champion vs Shadow Comparator.

- Champion: decision schema production output
- Challenger: existing Decision Shadow CloudWatch JSON events
- DB access: read-only
- Result: MATCH / DIFFERENCE / REVIEW_REQUIRED / INVALID
"""

import argparse
import json
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from port_strategy_decision.db_config import get_db_config


BUY_SUMMARY = "DECISION_SHADOW_BUY_SUMMARY"
BUY_SIGNAL = "DECISION_SHADOW_BUY_SIGNAL"
POSITION_SUMMARY = "DECISION_SHADOW_POSITION_SUMMARY"
POSITION_DECISION = "DECISION_SHADOW_POSITION_DECISION"

VALID_RESULTS = {
    "MATCH",
    "DIFFERENCE",
    "REVIEW_REQUIRED",
    "INVALID",
}


def _load_shadow_events(path: Path) -> list[dict]:
    events = []

    for line_no, raw_line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line:
            continue

        # Even if ordinary logs are mixed in before the CloudWatch string,
        # take only the lines that contain a JSON object.
        start = line.find("{")
        end = line.rfind("}")

        if start < 0 or end < start:
            continue

        candidate = line[start : end + 1]

        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        if isinstance(value, dict) and str(value.get("event", "")).startswith(
            "DECISION_SHADOW_"
        ):
            value["_source_line"] = line_no
            events.append(value)

    return events


def _single_event(events: list[dict], event_name: str) -> dict:
    matched = [item for item in events if item.get("event") == event_name]

    if len(matched) != 1:
        raise ValueError(
            f"{event_name} expected exactly 1 event, found {len(matched)}"
        )

    return matched[0]


def _reason_from_operating(row: dict) -> str:
    return str(
        row.get("sell_reason")
        or row.get("hold_reason")
        or row.get("skip_reason")
        or ""
    )


def _normalize(value):
    if value is None:
        return None

    return str(value)


def _validate_shadow(events: list[dict]) -> tuple[dict, dict]:
    if not events:
        raise ValueError("No Decision Shadow JSON events found.")

    buy_summary = _single_event(events, BUY_SUMMARY)
    position_summary = _single_event(events, POSITION_SUMMARY)

    for event in events:
        if event.get("write_count") != 0:
            raise ValueError(
                "Shadow write_count must be 0: "
                f"event={event.get('event')} "
                f"line={event.get('_source_line')} "
                f"write_count={event.get('write_count')}"
            )

    buy_run_date = _normalize(buy_summary.get("run_date"))
    buy_data_date = _normalize(buy_summary.get("data_date"))
    position_run_date = _normalize(position_summary.get("run_date"))
    position_data_date = _normalize(position_summary.get("data_date"))

    if not all(
        [
            buy_run_date,
            buy_data_date,
            position_run_date,
            position_data_date,
        ]
    ):
        raise ValueError("Shadow run_date/data_date is missing.")

    if (
        buy_run_date != position_run_date
        or buy_data_date != position_data_date
    ):
        raise ValueError(
            "BUY/Position Shadow evaluation context mismatch: "
            f"BUY={buy_run_date}/{buy_data_date}, "
            f"POSITION={position_run_date}/{position_data_date}"
        )

    for event in events:
        event_run_date = event.get("run_date")
        event_data_date = event.get("data_date")

        if event_run_date is not None and _normalize(event_run_date) != buy_run_date:
            raise ValueError(
                f"Shadow run_date mismatch at line={event.get('_source_line')}"
            )

        if event_data_date is not None and _normalize(event_data_date) != buy_data_date:
            raise ValueError(
                f"Shadow data_date mismatch at line={event.get('_source_line')}"
            )

    buy_signals = [
        item for item in events if item.get("event") == BUY_SIGNAL
    ]
    position_decisions = [
        item for item in events if item.get("event") == POSITION_DECISION
    ]

    if int(buy_summary.get("signal_count", -1)) != len(buy_signals):
        raise ValueError(
            "BUY signal_count does not match Shadow BUY event count."
        )

    if int(position_summary.get("decision_count", -1)) != len(
        position_decisions
    ):
        raise ValueError(
            "Position decision_count does not match Shadow event count."
        )

    buy_tickers = [item.get("ticker_code") for item in buy_signals]

    if None in buy_tickers or len(buy_tickers) != len(set(buy_tickers)):
        raise ValueError("Shadow BUY ticker identity is invalid or duplicated.")

    position_ids = [
        item.get("position_state_id") for item in position_decisions
    ]

    if None in position_ids or len(position_ids) != len(set(position_ids)):
        raise ValueError(
            "Shadow Position identity is invalid or duplicated."
        )

    return buy_summary, position_summary


def _load_operating(run_date: str, data_date: str) -> dict:
    conn = psycopg2.connect(**get_db_config())

    try:
        conn.set_session(readonly=True, autocommit=False)

        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                select
                    id,
                    run_date,
                    data_date,
                    run_status,
                    market_signal,
                    candidate_count,
                    signal_count
                from decision.strategy_daily_run
                where run_date = %s
                  and data_date = %s
                  and run_status = 'COMPLETED'
                order by id desc
                limit 1
                """,
                (run_date, data_date),
            )
            daily_run = cur.fetchone()

            if daily_run is None:
                raise ValueError(
                    "No COMPLETED operating Daily Run for "
                    f"run_date={run_date}, data_date={data_date}"
                )

            daily_run_id = daily_run["id"]

            cur.execute(
                """
                select
                    daily_run_id,
                    run_date,
                    data_date,
                    ticker_code,
                    company_name,
                    signal_type,
                    rank_no,
                    market_signal,
                    final_score,
                    position_size,
                    target_qty,
                    entry_reason,
                    processor_version
                from decision.strategy_daily_signal
                where daily_run_id = %s
                order by rank_no nulls last, ticker_code
                """,
                (daily_run_id,),
            )
            buy_signals = list(cur.fetchall())

            cur.execute(
                """
                select
                    daily_run_id,
                    run_date,
                    data_date,
                    position_state_id,
                    ticker_code,
                    stock_name,
                    decision_type,
                    decision_status,
                    sell_reason,
                    hold_reason,
                    skip_reason,
                    remaining_qty,
                    order_qty,
                    processor_version
                from decision.strategy_daily_position_decision
                where daily_run_id = %s
                order by position_state_id
                """,
                (daily_run_id,),
            )
            position_decisions = list(cur.fetchall())

        conn.rollback()

        return {
            "daily_run": dict(daily_run),
            "buy_signals": [dict(row) for row in buy_signals],
            "position_decisions": [
                dict(row) for row in position_decisions
            ],
        }

    finally:
        conn.rollback()
        conn.close()


def _compare_buy(
    operating_rows: list[dict],
    shadow_rows: list[dict],
) -> list[dict]:
    operating = {
        str(row["ticker_code"]): row
        for row in operating_rows
    }
    shadow = {
        str(row["ticker_code"]): row
        for row in shadow_rows
    }

    results = []

    for ticker in sorted(set(operating) | set(shadow)):
        op = operating.get(ticker)
        sh = shadow.get(ticker)

        if op is None:
            results.append(
                {
                    "area": "BUY",
                    "identity": ticker,
                    "result": "REVIEW_REQUIRED",
                    "change": "NEW_BUY",
                    "operating": None,
                    "shadow": {
                        "target_qty": sh.get("target_qty"),
                        "entry_reason": sh.get("entry_reason"),
                    },
                }
            )
            continue

        if sh is None:
            results.append(
                {
                    "area": "BUY",
                    "identity": ticker,
                    "result": "REVIEW_REQUIRED",
                    "change": "BUY_REMOVED",
                    "operating": {
                        "target_qty": op.get("target_qty"),
                        "entry_reason": op.get("entry_reason"),
                    },
                    "shadow": None,
                }
            )
            continue

        differences = []

        for field in (
            "target_qty",
            "entry_reason",
            "market_signal",
        ):
            if _normalize(op.get(field)) != _normalize(sh.get(field)):
                differences.append(field)

        results.append(
            {
                "area": "BUY",
                "identity": ticker,
                "result": "DIFFERENCE" if differences else "MATCH",
                "change": differences,
                "operating": {
                    "target_qty": op.get("target_qty"),
                    "entry_reason": op.get("entry_reason"),
                    "market_signal": op.get("market_signal"),
                },
                "shadow": {
                    "target_qty": sh.get("target_qty"),
                    "entry_reason": sh.get("entry_reason"),
                    "market_signal": sh.get("market_signal"),
                },
            }
        )

    return results


def _compare_position(
    operating_rows: list[dict],
    shadow_rows: list[dict],
) -> list[dict]:
    operating = {
        str(row["position_state_id"]): row
        for row in operating_rows
    }
    shadow = {
        str(row["position_state_id"]): row
        for row in shadow_rows
    }

    results = []

    for position_id in sorted(
        set(operating) | set(shadow),
        key=lambda value: int(value),
    ):
        op = operating.get(position_id)
        sh = shadow.get(position_id)

        if op is None or sh is None:
            results.append(
                {
                    "area": "POSITION",
                    "identity": position_id,
                    "ticker_code": (
                        op.get("ticker_code")
                        if op
                        else sh.get("ticker_code")
                    ),
                    "result": "REVIEW_REQUIRED",
                    "change": (
                        "POSITION_ADDED"
                        if op is None
                        else "POSITION_REMOVED"
                    ),
                    "operating": op,
                    "shadow": sh,
                }
            )
            continue

        op_decision = str(op.get("decision_type") or "").upper()
        sh_decision = str(sh.get("decision_type") or "").upper()

        if op_decision != sh_decision:
            result = "REVIEW_REQUIRED"
            differences = ["decision_type"]
        else:
            differences = []

            field_pairs = (
                (
                    "reason",
                    _reason_from_operating(op),
                    sh.get("reason"),
                ),
                (
                    "remaining_qty",
                    op.get("remaining_qty"),
                    sh.get("remaining_qty"),
                ),
                (
                    "order_qty",
                    op.get("order_qty"),
                    sh.get("order_qty"),
                ),
            )

            for field, op_value, sh_value in field_pairs:
                if _normalize(op_value) != _normalize(sh_value):
                    differences.append(field)

            result = "DIFFERENCE" if differences else "MATCH"

        results.append(
            {
                "area": "POSITION",
                "identity": position_id,
                "ticker_code": op.get("ticker_code"),
                "result": result,
                "change": differences,
                "operating": {
                    "decision_type": op_decision,
                    "reason": _reason_from_operating(op),
                    "remaining_qty": op.get("remaining_qty"),
                    "order_qty": op.get("order_qty"),
                },
                "shadow": {
                    "decision_type": sh_decision,
                    "reason": sh.get("reason"),
                    "remaining_qty": sh.get("remaining_qty"),
                    "order_qty": sh.get("order_qty"),
                },
            }
        )

    return results


def _overall_result(
    market_changed: bool,
    comparisons: list[dict],
) -> str:
    if market_changed:
        return "REVIEW_REQUIRED"

    results = {item["result"] for item in comparisons}

    if "REVIEW_REQUIRED" in results:
        return "REVIEW_REQUIRED"

    if "DIFFERENCE" in results:
        return "DIFFERENCE"

    return "MATCH"


def compare(shadow_path: Path) -> dict:
    events = _load_shadow_events(shadow_path)

    buy_summary, position_summary = _validate_shadow(events)

    run_date = str(buy_summary["run_date"])
    data_date = str(buy_summary["data_date"])

    operating = _load_operating(
        run_date=run_date,
        data_date=data_date,
    )

    operating_run = operating["daily_run"]

    market_changed = (
        _normalize(operating_run.get("market_signal"))
        != _normalize(buy_summary.get("market_signal"))
    )

    shadow_buy = [
        item for item in events
        if item.get("event") == BUY_SIGNAL
    ]
    shadow_position = [
        item for item in events
        if item.get("event") == POSITION_DECISION
    ]

    buy_comparisons = _compare_buy(
        operating["buy_signals"],
        shadow_buy,
    )
    position_comparisons = _compare_position(
        operating["position_decisions"],
        shadow_position,
    )

    comparisons = buy_comparisons + position_comparisons

    overall = _overall_result(
        market_changed=market_changed,
        comparisons=comparisons,
    )

    return {
        "result": overall,
        "run_date": run_date,
        "data_date": data_date,
        "operating_daily_run_id": operating_run["id"],
        "market": {
            "result": (
                "REVIEW_REQUIRED"
                if market_changed
                else "MATCH"
            ),
            "operating": operating_run.get("market_signal"),
            "shadow": buy_summary.get("market_signal"),
        },
        "shadow": {
            "buy_signal_count": buy_summary.get("signal_count"),
            "position_decision_count": position_summary.get(
                "decision_count"
            ),
            "position_evaluator_version": position_summary.get(
                "evaluator_version"
            ),
            "write_count": 0,
        },
        "summary": {
            "match": sum(
                1 for item in comparisons
                if item["result"] == "MATCH"
            ),
            "difference": sum(
                1 for item in comparisons
                if item["result"] == "DIFFERENCE"
            ),
            "review_required": sum(
                1 for item in comparisons
                if item["result"] == "REVIEW_REQUIRED"
            ),
        },
        "comparisons": comparisons,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--shadow-jsonl",
        required=True,
        help="File containing Decision Shadow CloudWatch JSON lines.",
    )
    parser.add_argument(
        "--output",
        default="decision-comparison-report.json",
    )
    args = parser.parse_args()

    output_path = Path(args.output)

    try:
        report = compare(Path(args.shadow_jsonl))

        if report["result"] not in VALID_RESULTS:
            raise RuntimeError(
                f"Invalid comparator result={report['result']}"
            )

        exit_code = 0

    except Exception as exc:
        report = {
            "result": "INVALID",
            "error": str(exc),
        }
        exit_code = 2

    output_path.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )
    print(f"DECISION_COMPARISON_RESULT={report['result']}")
    print(f"DECISION_COMPARISON_REPORT={output_path}")

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()

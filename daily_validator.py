"""Validation entrypoint that queries and prints the latest daily buy signal execution results.

Reads `strategy_daily_run` and `strategy_daily_signal` from the DB and displays
them on the console. There are no write operations, but because operational data
and sensitive information may be exposed, confirmation is required before running.
"""

import argparse

import psycopg2

from port_strategy_decision.db_config import get_db_config
from port_strategy_decision.daily_repository import (
    get_latest_daily_run,
    get_daily_signals,
)


def get_conn():
    return psycopg2.connect(**get_db_config())


def print_daily_run(run):
    if not run:
        print("No strategy_daily_run found.")
        return

    print("===== LATEST DAILY RUN =====")
    print("id:", run["id"])
    print("strategy:", run["strategy_name"])
    print("version:", run["strategy_version"])
    print("run_date:", run["run_date"])
    print("data_date:", run["data_date"])
    print("run_type:", run["run_type"])
    print("run_status:", run["run_status"])
    print("market_signal:", run["market_signal"])
    print("base_exposure:", run["base_exposure"])
    print("max_positions:", run["max_positions"])
    print("candidate_count:", run["candidate_count"])
    print("signal_count:", run["signal_count"])
    print("started_at:", run["started_at"])
    print("finished_at:", run["finished_at"])

    if run.get("error_message"):
        print("error_message:", run["error_message"])


def print_daily_signals(signals):
    print()
    print("===== DAILY SIGNALS =====")
    print("signal_count:", len(signals))

    for signal in signals:
        print(
            signal["rank_no"],
            signal["ticker_code"],
            signal["company_name"],
            signal["signal_type"],
            signal["signal_status"],
            "market=",
            signal["market_signal"],
            "score=",
            signal["final_score"],
            "flow=",
            signal["flow_score"],
            "size=",
            signal["position_size"],
            "reason=",
            signal["entry_reason"],
        )


def validate_latest_daily_run():
    """Query and print the BUY signal list associated with the latest daily run."""
    conn = get_conn()

    try:
        run = get_latest_daily_run(conn)
        print_daily_run(run)

        if not run:
            return None

        signals = get_daily_signals(conn, run["id"])
        print_daily_signals(signals)

        return {
            "run": run,
            "signals": signals,
        }

    finally:
        conn.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Validate latest daily strategy signal run.")
    return parser.parse_args()


if __name__ == "__main__":
    parse_args()
    validate_latest_daily_run()

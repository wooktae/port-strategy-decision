"""Backtest-style entrypoint that generates a single-date decision snapshot.

Loads the market/stock features from the DB and prints the market/filter/sizing
results. Do not run this during documentation work or cleanup work without
operational approval.
"""

import psycopg2
import psycopg2.extras

from port_strategy_common.config import DECISION_RUN_DATE
from port_strategy_decision.backtest_market import evaluate_market
from port_strategy_decision.backtest_filter import filter_buy_candidates
from port_strategy_decision.backtest_sizing import allocate_positions
from port_strategy_decision.db_config import get_db_config


def get_conn():
    return psycopg2.connect(**get_db_config())


def load_market(conn, date):
    sql = """
    SELECT *
    FROM pre_total_market_daily_feature
    WHERE date = %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (date,))
        return cur.fetchone()


def load_stocks(conn, date):
    sql = """
    SELECT *
    FROM pre_total_stock_daily_feature
    WHERE date = %s
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (date,))
        return cur.fetchall()


def run(date):
    """Read DB features and print the single-date market/filter/sizing results."""
    conn = get_conn()

    try:
        market = load_market(conn, date)
        stocks = load_stocks(conn, date)

        decision = evaluate_market(market)
        candidates = filter_buy_candidates(stocks, decision)
        positions = allocate_positions(candidates, decision)

        print("===== RESULT =====")
        print("market:", decision)
        print("candidates:", len(candidates))
        print("positions:", len(positions))

        for p in positions[:5]:
            print(p["ticker_code"], float(p["position_size"]))

    finally:
        conn.close()


if __name__ == "__main__":
    run(DECISION_RUN_DATE)

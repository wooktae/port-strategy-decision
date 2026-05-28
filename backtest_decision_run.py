"""단일 일자 decision snapshot을 생성하는 backtest 성격 entrypoint.

market/stock feature를 DB에서 조회하고 run 기록을 생성한 뒤 market/filter/sizing
결과를 출력한다. 문서화 작업이나 운영 승인 없는 정리 작업 중에는 실행하지 않는다.
"""

import psycopg2
import psycopg2.extras

from port_strategy_common.config import DECISION_RUN_DATE
from port_strategy_decision.backtest_market import evaluate_market
from port_strategy_decision.backtest_filter import filter_buy_candidates
from port_strategy_decision.backtest_sizing import allocate_positions
from port_strategy_decision.db_config import get_db_config
from port_strategy_common.run_store import create_run, ensure_run_tables


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
    """DB feature를 읽어 단일 일자 market/filter/sizing 결과를 출력한다."""
    conn = get_conn()

    try:
        ensure_run_tables(conn)
        run_id = create_run(
            conn,
            run_mode="DECISION",
            run_note="single day decision snapshot",
            run_date=date,
        )

        market = load_market(conn, date)
        stocks = load_stocks(conn, date)

        decision = evaluate_market(market)
        candidates = filter_buy_candidates(stocks, decision)
        positions = allocate_positions(candidates, decision)

        print("RUN ID:", run_id)
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

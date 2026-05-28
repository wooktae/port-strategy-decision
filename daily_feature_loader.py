"""daily decision 입력 feature를 조회하는 loader 모듈.

run date/data date를 결정하고 `pre_total_market_daily_feature`,
`pre_total_stock_daily_feature`, `stock_universe`를 조회한다. DB 연결은 호출자가 열고 닫는다.
"""

import datetime
from typing import Optional

import psycopg2.extras


def resolve_run_date(run_date: Optional[str] = None) -> datetime.date:
    if run_date:
        return datetime.date.fromisoformat(str(run_date))

    return datetime.date.today()


def resolve_latest_data_date(conn) -> datetime.date:
    sql = """
    SELECT MAX(date) AS data_date
    FROM pre_total_market_daily_feature
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        row = cur.fetchone()

    if not row or not row["data_date"]:
        raise RuntimeError("No data_date found in pre_total_market_daily_feature.")

    return row["data_date"]


def resolve_data_date(conn, data_date: Optional[str] = None) -> datetime.date:
    if data_date:
        return datetime.date.fromisoformat(str(data_date))

    return resolve_latest_data_date(conn)


def load_market_feature(conn, data_date):
    sql = """
    SELECT *
    FROM pre_total_market_daily_feature
    WHERE date = %s
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (data_date,))
        row = cur.fetchone()

    if not row:
        raise RuntimeError(f"No market feature found for data_date={data_date}")

    return row


def load_stock_features(conn, data_date):
    sql = """
    SELECT
        s.*,
        COALESCE(u.company_name, s.ticker_code) AS company_name
    FROM pre_total_stock_daily_feature s
    LEFT JOIN stock_universe u
           ON u.ticker_code = s.ticker_code
    WHERE s.date = %s
    ORDER BY s.ticker_code ASC
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (data_date,))
        rows = cur.fetchall()

    if not rows:
        raise RuntimeError(f"No stock features found for data_date={data_date}")

    return rows


def load_daily_features(conn, run_date: Optional[str] = None, data_date: Optional[str] = None):
    """daily buy signal 생성에 필요한 market/stock feature 묶음을 반환한다."""
    resolved_run_date = resolve_run_date(run_date)
    resolved_data_date = resolve_data_date(conn, data_date)

    market = load_market_feature(conn, resolved_data_date)
    stocks = load_stock_features(conn, resolved_data_date)

    return {
        "run_date": resolved_run_date,
        "data_date": resolved_data_date,
        "market": market,
        "stocks": stocks,
    }

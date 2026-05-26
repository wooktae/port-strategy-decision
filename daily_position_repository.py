# C:\Workspaces\port_strategy_decision\daily_position_repository.py

import json
from decimal import Decimal
from typing import Any, Optional

import psycopg2.extras

from port_strategy_common.config import DB_CONFIG, STRATEGY_NAME, ENGINE_VERSION


ACTIVE_POSITION_STATUSES = ("OPEN", "SELL_READY", "SELL_ORDERED")


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def json_default(value: Any):
    if isinstance(value, Decimal):
        return str(value)

    return str(value)


def dumps_json(value: Any):
    if value is None:
        return None

    if isinstance(value, str):
        return value

    return json.dumps(value, ensure_ascii=False, default=json_default)


def get_latest_daily_run(conn):
    sql = """
    SELECT
        *
    FROM strategy_daily_run
    WHERE strategy_name = %s
      AND strategy_version = %s
      AND run_type = 'DAILY_SIGNAL'
      AND run_status = 'COMPLETED'
    ORDER BY run_date DESC, data_date DESC, id DESC
    LIMIT 1
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (STRATEGY_NAME, ENGINE_VERSION))
        row = cur.fetchone()

    if not row:
        raise RuntimeError("No completed strategy_daily_run found.")

    return row


def get_active_position_states(conn, account_no: Optional[str] = None):
    params = []

    sql = """
    SELECT
        *
    FROM strategy_position_state
    WHERE position_status IN ('OPEN', 'SELL_READY', 'SELL_ORDERED')
    """

    if account_no:
        sql += " AND account_no = %s "
        params.append(account_no)

    sql += """
    ORDER BY entry_date ASC NULLS LAST, id ASC
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def get_latest_broker_position(conn, account_id, ticker_code):
    """
    최신 balance snapshot 기준 broker position 조회.

    중요:
    - connector_balance.py 실행 결과 현재 보유종목이 0건이면
      connector_position_snapshot에는 최신 날짜 row가 없을 수 있다.
    - connector_position_snapshot 자체의 최신 row를 현재 보유로 보면
      전량 매도된 과거 보유종목을 아직 보유 중으로 착각할 수 있다.
    - 따라서 최신 connector_balance_snapshot의 as_of_date와 같은 날짜의 position row만 현재 보유로 인정한다.
    """

    sql = """
    WITH latest_balance AS (
        SELECT
            account_id,
            as_of_date,
            as_of_ts
        FROM connector_balance_snapshot
        WHERE account_id = %s
        ORDER BY as_of_date DESC, as_of_ts DESC, id DESC
        LIMIT 1
    )
    SELECT
        cps.*
    FROM latest_balance lb
    JOIN connector_position_snapshot cps
      ON cps.account_id = lb.account_id
     AND cps.as_of_date = lb.as_of_date
    WHERE cps.account_id = %s
      AND cps.ticker_code = %s
      AND COALESCE(cps.quantity, 0) > 0
    ORDER BY cps.as_of_ts DESC, cps.id DESC
    LIMIT 1
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (account_id, account_id, ticker_code))
        return cur.fetchone()


def get_stock_feature(conn, ticker_code, data_date):
    sql = """
    SELECT
        *
    FROM pre_total_stock_daily_feature
    WHERE ticker_code = %s
      AND date <= %s
    ORDER BY date DESC
    LIMIT 1
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (ticker_code, data_date))
        return cur.fetchone()


def get_market_feature(conn, data_date):
    sql = """
    SELECT
        *
    FROM pre_total_market_daily_feature
    WHERE date <= %s
    ORDER BY date DESC
    LIMIT 1
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (data_date,))
        return cur.fetchone()


def upsert_daily_position_decision(conn, decision: dict):
    sql = """
    INSERT INTO strategy_daily_position_decision (
        daily_run_id,
        strategy_name,
        strategy_version,
        run_date,
        data_date,
        decision_date,

        position_state_id,
        account_id,
        account_no,

        ticker_code,
        stock_name,

        decision_type,
        decision_status,

        sell_reason,
        hold_reason,
        skip_reason,

        holding_days,

        entry_date,
        entry_price,
        entry_qty,
        remaining_qty,

        current_price,
        current_qty,
        sellable_qty,

        expected_pnl_amount,
        expected_pnl_rate,

        market_signal,
        market_regime_score,

        flow_score,
        info_score,
        tape_score,
        final_score,
        short_pressure_score,

        order_qty,
        order_price,
        target_amount,

        position_context,
        sell_info,
        validation_result,
        raw_stock_feature,
        raw_market_feature,

        source_table,
        processor_version,

        execution_order_id,
        error_message
    )
    VALUES (
        %(daily_run_id)s,
        %(strategy_name)s,
        %(strategy_version)s,
        %(run_date)s,
        %(data_date)s,
        %(decision_date)s,

        %(position_state_id)s,
        %(account_id)s,
        %(account_no)s,

        %(ticker_code)s,
        %(stock_name)s,

        %(decision_type)s,
        %(decision_status)s,

        %(sell_reason)s,
        %(hold_reason)s,
        %(skip_reason)s,

        %(holding_days)s,

        %(entry_date)s,
        %(entry_price)s,
        %(entry_qty)s,
        %(remaining_qty)s,

        %(current_price)s,
        %(current_qty)s,
        %(sellable_qty)s,

        %(expected_pnl_amount)s,
        %(expected_pnl_rate)s,

        %(market_signal)s,
        %(market_regime_score)s,

        %(flow_score)s,
        %(info_score)s,
        %(tape_score)s,
        %(final_score)s,
        %(short_pressure_score)s,

        %(order_qty)s,
        %(order_price)s,
        %(target_amount)s,

        %(position_context)s::jsonb,
        %(sell_info)s::jsonb,
        %(validation_result)s::jsonb,
        %(raw_stock_feature)s::jsonb,
        %(raw_market_feature)s::jsonb,

        %(source_table)s,
        %(processor_version)s,

        %(execution_order_id)s,
        %(error_message)s
    )
    ON CONFLICT (daily_run_id, position_state_id, decision_date)
    DO UPDATE SET
        strategy_name = EXCLUDED.strategy_name,
        strategy_version = EXCLUDED.strategy_version,
        run_date = EXCLUDED.run_date,
        data_date = EXCLUDED.data_date,

        account_id = EXCLUDED.account_id,
        account_no = EXCLUDED.account_no,

        ticker_code = EXCLUDED.ticker_code,
        stock_name = EXCLUDED.stock_name,

        decision_type = EXCLUDED.decision_type,
        decision_status = EXCLUDED.decision_status,

        sell_reason = EXCLUDED.sell_reason,
        hold_reason = EXCLUDED.hold_reason,
        skip_reason = EXCLUDED.skip_reason,

        holding_days = EXCLUDED.holding_days,

        entry_date = EXCLUDED.entry_date,
        entry_price = EXCLUDED.entry_price,
        entry_qty = EXCLUDED.entry_qty,
        remaining_qty = EXCLUDED.remaining_qty,

        current_price = EXCLUDED.current_price,
        current_qty = EXCLUDED.current_qty,
        sellable_qty = EXCLUDED.sellable_qty,

        expected_pnl_amount = EXCLUDED.expected_pnl_amount,
        expected_pnl_rate = EXCLUDED.expected_pnl_rate,

        market_signal = EXCLUDED.market_signal,
        market_regime_score = EXCLUDED.market_regime_score,

        flow_score = EXCLUDED.flow_score,
        info_score = EXCLUDED.info_score,
        tape_score = EXCLUDED.tape_score,
        final_score = EXCLUDED.final_score,
        short_pressure_score = EXCLUDED.short_pressure_score,

        order_qty = EXCLUDED.order_qty,
        order_price = EXCLUDED.order_price,
        target_amount = EXCLUDED.target_amount,

        position_context = EXCLUDED.position_context,
        sell_info = EXCLUDED.sell_info,
        validation_result = EXCLUDED.validation_result,
        raw_stock_feature = EXCLUDED.raw_stock_feature,
        raw_market_feature = EXCLUDED.raw_market_feature,

        source_table = EXCLUDED.source_table,
        processor_version = EXCLUDED.processor_version,

        execution_order_id = COALESCE(strategy_daily_position_decision.execution_order_id, EXCLUDED.execution_order_id),
        error_message = EXCLUDED.error_message,
        updated_at = now()
    RETURNING id
    """

    with conn.cursor() as cur:
        cur.execute(sql, decision)
        return cur.fetchone()[0]


def update_position_state_latest_evaluation(conn, decision: dict):
    """
    Daily Position Decision 결과를 기존 strategy_position_state latest_*에도 반영.
    기존 View/Position lifecycle 화면과 호환 목적.
    """

    sql = """
    UPDATE strategy_position_state
    SET
        last_evaluated_date = %(decision_date)s,
        latest_sell_reason = %(reason)s,
        latest_sell_info = %(sell_info)s::jsonb,
        latest_validation_result = %(validation_result)s::jsonb,
        updated_at = now()
    WHERE id = %(position_state_id)s
    RETURNING id
    """

    reason = (
        decision.get("sell_reason")
        or decision.get("hold_reason")
        or decision.get("skip_reason")
    )

    with conn.cursor() as cur:
        cur.execute(
            sql,
            {
                "decision_date": decision["decision_date"],
                "reason": reason,
                "sell_info": decision["sell_info"],
                "validation_result": decision["validation_result"],
                "position_state_id": decision["position_state_id"],
            },
        )
        row = cur.fetchone()

    return row[0] if row else None


def update_daily_position_decision_execution_order(conn, decision_id: int, execution_order_id: int):
    sql = """
    UPDATE strategy_daily_position_decision
    SET
        execution_order_id = %s,
        decision_status = 'EXECUTION_CREATED',
        updated_at = now()
    WHERE id = %s
    RETURNING id
    """

    with conn.cursor() as cur:
        cur.execute(sql, (execution_order_id, decision_id))
        row = cur.fetchone()

    return row[0] if row else None


def get_daily_position_decisions(conn, daily_run_id: int):
    sql = """
    SELECT
        *
    FROM strategy_daily_position_decision
    WHERE daily_run_id = %s
    ORDER BY
        CASE decision_type
            WHEN 'SELL' THEN 1
            WHEN 'HOLD' THEN 2
            WHEN 'SKIP' THEN 3
            ELSE 9
        END,
        ticker_code ASC,
        id ASC
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (daily_run_id,))
        return cur.fetchall()
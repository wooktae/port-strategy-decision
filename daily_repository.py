"""daily buy signal 실행 결과 저장 repository 모듈.

`strategy_daily_run`과 `strategy_daily_signal`의 생성, 갱신, 조회를 담당한다.
DB schema/table/unique key/upsert 정책은 운영 계약이므로 문서화 외 변경하지 않는다.
"""

import json
from decimal import Decimal
from typing import Any, Optional

import psycopg2.extras

from port_strategy_common.config import STRATEGY_NAME, ENGINE_VERSION, get_config_snapshot


def _json_default(value: Any):
    if isinstance(value, Decimal):
        return str(value)

    return str(value)


def to_jsonb(value: Any):
    if value is None:
        return None

    return json.dumps(value, default=_json_default, ensure_ascii=False)


def create_or_replace_daily_run(
    conn,
    run_date,
    data_date,
    run_type: str = "DAILY_SIGNAL",
    run_note: Optional[str] = None,
):
    """동일 run key의 daily run을 RUNNING 상태로 만들고 기존 signal을 정리한다."""
    config_snapshot = get_config_snapshot()

    sql = """
    INSERT INTO strategy_daily_run (
        strategy_name,
        strategy_version,
        run_date,
        data_date,
        run_type,
        run_status,
        run_note,
        config_snapshot,
        started_at
    )
    VALUES (
        %s, %s, %s, %s, %s,
        'RUNNING',
        %s,
        %s::jsonb,
        now()
    )
    ON CONFLICT (strategy_name, strategy_version, run_date, data_date, run_type)
    DO UPDATE SET
        run_status = 'RUNNING',
        market_signal = NULL,
        base_exposure = NULL,
        max_positions = NULL,
        candidate_count = 0,
        signal_count = 0,
        run_note = EXCLUDED.run_note,
        error_message = NULL,
        config_snapshot = EXCLUDED.config_snapshot,
        started_at = now(),
        finished_at = NULL,
        updated_at = now()
    RETURNING id
    """

    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                STRATEGY_NAME,
                ENGINE_VERSION,
                run_date,
                data_date,
                run_type,
                run_note,
                to_jsonb(config_snapshot),
            ),
        )
        daily_run_id = cur.fetchone()[0]

    delete_daily_signals(conn, daily_run_id)

    return daily_run_id


def delete_daily_signals(conn, daily_run_id: int):
    sql = """
    DELETE FROM strategy_daily_signal
    WHERE daily_run_id = %s
    """

    with conn.cursor() as cur:
        cur.execute(sql, (daily_run_id,))


def update_daily_run_success(
    conn,
    daily_run_id: int,
    decision,
    candidate_count: int,
    signal_count: int,
):
    sql = """
    UPDATE strategy_daily_run
    SET
        run_status = 'COMPLETED',
        market_signal = %s,
        base_exposure = %s,
        max_positions = %s,
        candidate_count = %s,
        signal_count = %s,
        error_message = NULL,
        finished_at = now(),
        updated_at = now()
    WHERE id = %s
    """

    with conn.cursor() as cur:
        cur.execute(
            sql,
            (
                getattr(decision, "signal_type", None),
                getattr(decision, "base_exposure", None),
                getattr(decision, "max_positions", None),
                candidate_count,
                signal_count,
                daily_run_id,
            ),
        )


def update_daily_run_failed(conn, daily_run_id: int, error_message: str):
    sql = """
    UPDATE strategy_daily_run
    SET
        run_status = 'FAILED',
        error_message = %s,
        finished_at = now(),
        updated_at = now()
    WHERE id = %s
    """

    with conn.cursor() as cur:
        cur.execute(sql, (error_message, daily_run_id))


def insert_daily_signal(conn, signal: dict):
    """`strategy_daily_signal`에 BUY signal 1건을 upsert한다."""
    sql = """
    INSERT INTO strategy_daily_signal (
        daily_run_id,
        strategy_name,
        strategy_version,
        run_date,
        data_date,
        signal_date,
        ticker_code,
        company_name,
        signal_type,
        signal_status,
        rank_no,
        market_signal,
        base_exposure,
        final_score,
        flow_score,
        tape_score,
        info_score,
        short_score,
        volatility_20d,
        intraday_range,
        position_size,
        target_amount,
        target_qty,
        entry_reason,
        block_reason,
        buy_info,
        raw_features,
        source_table,
        processor_version
    )
    VALUES (
        %(daily_run_id)s,
        %(strategy_name)s,
        %(strategy_version)s,
        %(run_date)s,
        %(data_date)s,
        %(signal_date)s,
        %(ticker_code)s,
        %(company_name)s,
        %(signal_type)s,
        %(signal_status)s,
        %(rank_no)s,
        %(market_signal)s,
        %(base_exposure)s,
        %(final_score)s,
        %(flow_score)s,
        %(tape_score)s,
        %(info_score)s,
        %(short_score)s,
        %(volatility_20d)s,
        %(intraday_range)s,
        %(position_size)s,
        %(target_amount)s,
        %(target_qty)s,
        %(entry_reason)s,
        %(block_reason)s,
        %(buy_info)s::jsonb,
        %(raw_features)s::jsonb,
        %(source_table)s,
        %(processor_version)s
    )
    ON CONFLICT (daily_run_id, ticker_code, signal_type)
    DO UPDATE SET
        company_name = EXCLUDED.company_name,
        signal_status = EXCLUDED.signal_status,
        rank_no = EXCLUDED.rank_no,
        market_signal = EXCLUDED.market_signal,
        base_exposure = EXCLUDED.base_exposure,
        final_score = EXCLUDED.final_score,
        flow_score = EXCLUDED.flow_score,
        tape_score = EXCLUDED.tape_score,
        info_score = EXCLUDED.info_score,
        short_score = EXCLUDED.short_score,
        volatility_20d = EXCLUDED.volatility_20d,
        intraday_range = EXCLUDED.intraday_range,
        position_size = EXCLUDED.position_size,
        target_amount = EXCLUDED.target_amount,
        target_qty = EXCLUDED.target_qty,
        entry_reason = EXCLUDED.entry_reason,
        block_reason = EXCLUDED.block_reason,
        buy_info = EXCLUDED.buy_info,
        raw_features = EXCLUDED.raw_features,
        source_table = EXCLUDED.source_table,
        processor_version = EXCLUDED.processor_version,
        updated_at = now()
    RETURNING id
    """

    with conn.cursor() as cur:
        cur.execute(sql, signal)
        return cur.fetchone()[0]


def insert_daily_signals(conn, signals: list[dict]):
    signal_ids = []

    for signal in signals:
        signal_ids.append(insert_daily_signal(conn, signal))

    return signal_ids


def get_latest_daily_run(conn):
    sql = """
    SELECT *
    FROM strategy_daily_run
    ORDER BY started_at DESC, id DESC
    LIMIT 1
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql)
        return cur.fetchone()


def get_daily_signals(conn, daily_run_id: int):
    sql = """
    SELECT *
    FROM strategy_daily_signal
    WHERE daily_run_id = %s
    ORDER BY rank_no ASC NULLS LAST, id ASC
    """

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, (daily_run_id,))
        return cur.fetchall()

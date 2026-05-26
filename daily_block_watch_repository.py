from __future__ import annotations

import json
from decimal import Decimal
from typing import Any


def _to_jsonb(value: Any) -> str:
    if value is None:
        return "{}"

    return json.dumps(value, ensure_ascii=False, default=str)


def _to_decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None

    try:
        return Decimal(str(value))
    except Exception:
        return None


def insert_block_watch_candidates(conn, candidates: list[dict[str, Any]]) -> int:
    """
    BLOCK Watch 후보를 저장한다.

    중요:
    - strategy_daily_signal에는 저장하지 않는다.
    - strategy_execution_order도 만들지 않는다.
    - 관찰/검증용 테이블에만 저장한다.
    """

    if not candidates:
        return 0

    sql = """
        INSERT INTO strategy_block_watch_candidate (
            daily_run_id,
            run_date,
            data_date,
            ticker_code,
            stock_name,
            market_signal,
            watch_status,
            flow_score,
            final_score,
            info_score,
            volatility_20d,
            intraday_range,
            short_pressure_score,
            watch_reason,
            watch_detail,
            close_price,
            created_at,
            updated_at
        )
        VALUES (
            %(daily_run_id)s,
            %(run_date)s,
            %(data_date)s,
            %(ticker_code)s,
            %(stock_name)s,
            %(market_signal)s,
            %(watch_status)s,
            %(flow_score)s,
            %(final_score)s,
            %(info_score)s,
            %(volatility_20d)s,
            %(intraday_range)s,
            %(short_pressure_score)s,
            %(watch_reason)s,
            %(watch_detail)s::jsonb,
            %(close_price)s,
            NOW(),
            NOW()
        )
        ON CONFLICT (daily_run_id, ticker_code)
        DO UPDATE SET
            stock_name = EXCLUDED.stock_name,
            market_signal = EXCLUDED.market_signal,
            watch_status = EXCLUDED.watch_status,
            flow_score = EXCLUDED.flow_score,
            final_score = EXCLUDED.final_score,
            info_score = EXCLUDED.info_score,
            volatility_20d = EXCLUDED.volatility_20d,
            intraday_range = EXCLUDED.intraday_range,
            short_pressure_score = EXCLUDED.short_pressure_score,
            watch_reason = EXCLUDED.watch_reason,
            watch_detail = EXCLUDED.watch_detail,
            close_price = EXCLUDED.close_price,
            updated_at = NOW()
    """

    normalized_candidates = []
    for candidate in candidates:
        normalized_candidates.append(
            {
                "daily_run_id": candidate.get("daily_run_id"),
                "run_date": candidate.get("run_date"),
                "data_date": candidate.get("data_date"),
                "ticker_code": candidate.get("ticker_code"),
                "stock_name": candidate.get("stock_name"),
                "market_signal": candidate.get("market_signal", "BLOCK"),
                "watch_status": candidate.get("watch_status", "WATCH"),
                "flow_score": _to_decimal_or_none(candidate.get("flow_score")),
                "final_score": _to_decimal_or_none(candidate.get("final_score")),
                "info_score": _to_decimal_or_none(candidate.get("info_score")),
                "volatility_20d": _to_decimal_or_none(candidate.get("volatility_20d")),
                "intraday_range": _to_decimal_or_none(candidate.get("intraday_range")),
                "short_pressure_score": _to_decimal_or_none(candidate.get("short_pressure_score")),
                "watch_reason": candidate.get("watch_reason"),
                "watch_detail": _to_jsonb(candidate.get("watch_detail")),
                "close_price": _to_decimal_or_none(candidate.get("close_price")),
            }
        )

    with conn.cursor() as cur:
        cur.executemany(sql, normalized_candidates)

    return len(normalized_candidates)

def delete_block_watch_candidates(conn, daily_run_id: int) -> int:
    """
    daily_run 재실행 시 기존 Block Watch 후보를 지운다.

    이유:
    - create_or_replace_daily_run은 같은 run_date/data_date/run_type이면 daily_run_id를 재사용한다.
    - 기존 후보가 남아 있으면 기준 변경/데이터 변경 후에도 오래된 Watch 후보가 남을 수 있다.
    """

    sql = """
        DELETE FROM strategy_block_watch_candidate
        WHERE daily_run_id = %s
    """

    with conn.cursor() as cur:
        cur.execute(sql, (daily_run_id,))
        return cur.rowcount
    
"""Queries against public.fx_rates — daily CBU exchange-rate history.

Every datapoint is stored with its date so week-over-week / month-over-month
changes are computed here from real stored history (get_change), never asked
of the LLM.
"""
from datetime import date, timedelta

import asyncpg


async def upsert_rate(
    pool: asyncpg.Pool,
    *,
    currency_code: str,
    nominal: int,
    rate_uzs: float,
    diff_uzs: float | None,
    rate_date: date,
) -> None:
    await pool.execute(
        """
        INSERT INTO fx_rates (currency_code, nominal, rate_uzs, diff_uzs, rate_date)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (currency_code, rate_date) DO UPDATE
        SET rate_uzs = $3, diff_uzs = $4, nominal = $2
        """,
        currency_code, nominal, rate_uzs, diff_uzs, rate_date,
    )


async def get_latest(pool: asyncpg.Pool, currency_code: str) -> asyncpg.Record | None:
    return await pool.fetchrow(
        "SELECT * FROM fx_rates WHERE currency_code = $1 ORDER BY rate_date DESC LIMIT 1",
        currency_code,
    )


async def get_on_or_before(pool: asyncpg.Pool, currency_code: str, target_date: date) -> asyncpg.Record | None:
    return await pool.fetchrow(
        """
        SELECT * FROM fx_rates
        WHERE currency_code = $1 AND rate_date <= $2
        ORDER BY rate_date DESC LIMIT 1
        """,
        currency_code, target_date,
    )


async def get_change(pool: asyncpg.Pool, currency_code: str, days: int) -> dict | None:
    """Compares the latest stored rate against the closest stored rate
    `days` ago. Returns None if there isn't enough history yet."""
    latest = await get_latest(pool, currency_code)
    if not latest:
        return None
    past = await get_on_or_before(pool, currency_code, latest["rate_date"] - timedelta(days=days))
    if not past or past["rate_date"] == latest["rate_date"]:
        return None

    latest_rate = float(latest["rate_uzs"])
    past_rate = float(past["rate_uzs"])
    abs_change = latest_rate - past_rate
    pct_change = (abs_change / past_rate) * 100 if past_rate else 0.0

    return {
        "currency_code": currency_code,
        "latest_rate": latest_rate,
        "latest_date": latest["rate_date"].isoformat(),
        "past_rate": past_rate,
        "past_date": past["rate_date"].isoformat(),
        "days": days,
        "abs_change": abs_change,
        "pct_change": pct_change,
    }

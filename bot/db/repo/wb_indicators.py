"""Queries against public.wb_indicators — World Bank Open Data observations
for Uzbekistan and South Korea (see bot/ingestion/worldbank.py)."""
import asyncpg


async def upsert(
    pool: asyncpg.Pool,
    *,
    country_code: str,
    indicator_code: str,
    indicator_label: str,
    year: int,
    value: float | None,
) -> None:
    await pool.execute(
        """
        INSERT INTO wb_indicators (country_code, indicator_code, indicator_label, year, value)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (country_code, indicator_code, year) DO UPDATE
        SET value = $5, indicator_label = $3
        """,
        country_code, indicator_code, indicator_label, year, value,
    )


async def get_latest(pool: asyncpg.Pool, country_code: str, indicator_code: str) -> asyncpg.Record | None:
    return await pool.fetchrow(
        """
        SELECT * FROM wb_indicators
        WHERE country_code = $1 AND indicator_code = $2 AND value IS NOT NULL
        ORDER BY year DESC LIMIT 1
        """,
        country_code, indicator_code,
    )

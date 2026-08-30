"""Central Bank of Uzbekistan daily exchange-rate ingestion — no API key.

Fetches the CBU's public JSON feed once a day and stores every priority
currency's rate with its date, so week-over-week / month-over-month changes
can be computed later from real stored history (see
bot/db/repo/fx_rates.py:get_change) instead of asked of the LLM.
"""
import logging
from datetime import datetime

import httpx

from bot.db.repo import fx_rates as fx_repo

logger = logging.getLogger(__name__)

CBU_URL = "https://cbu.uz/uz/arkhiv-kursov-valyut/json/"

# KRW first: highest-value currency for this audience (Korea study/work diaspora).
PRIORITY_CURRENCIES = ("KRW", "USD", "RUB", "EUR")


async def fetch_and_store(pool) -> int:
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(CBU_URL)
        resp.raise_for_status()
        data = resp.json()

    stored = 0
    for row in data:
        if row.get("Ccy") not in PRIORITY_CURRENCIES:
            continue
        try:
            rate_date = datetime.strptime(row["Date"], "%d.%m.%Y").date()
            await fx_repo.upsert_rate(
                pool,
                currency_code=row["Ccy"],
                nominal=int(row["Nominal"]),
                rate_uzs=float(row["Rate"]),
                diff_uzs=float(row["Diff"]) if row.get("Diff") not in (None, "") else None,
                rate_date=rate_date,
            )
            stored += 1
        except Exception:
            logger.exception("Failed to store CBU rate row: %s", row)
    return stored

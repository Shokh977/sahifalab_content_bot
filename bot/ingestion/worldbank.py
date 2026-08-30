"""World Bank Open Data API ingestion — no key required.

Fetches a small set of Uzbekistan-relevant indicators, and the same for
South Korea (for diaspora comparisons), and stores every observation with
its year so posts can cite real, sourced macro figures instead of a vague
"experts say" framing.
"""
import logging

import httpx

from bot.db.repo import wb_indicators as wb_repo

logger = logging.getLogger(__name__)

BASE_URL = "https://api.worldbank.org/v2/country/{country}/indicator/{indicator}"

INDICATORS = {
    "FP.CPI.TOTL.ZG": "Inflation, consumer prices (annual %)",
    "BX.TRF.PWKR.CD.DT": "Personal remittances received (current US$)",
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
    "SL.UEM.TOTL.ZS": "Unemployment, total (% of labor force)",
}
COUNTRIES = ("UZB", "KOR")


async def fetch_indicator(country: str, indicator: str) -> list[dict]:
    url = BASE_URL.format(country=country, indicator=indicator)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params={"format": "json", "per_page": "20"})
        resp.raise_for_status()
        data = resp.json()
    if not isinstance(data, list) or len(data) < 2 or not data[1]:
        return []
    return [
        {"year": int(row["date"]), "value": row["value"]}
        for row in data[1]
        if row.get("value") is not None
    ]


async def fetch_all(pool) -> int:
    stored = 0
    for country in COUNTRIES:
        for indicator, label in INDICATORS.items():
            try:
                rows = await fetch_indicator(country, indicator)
            except Exception:
                logger.exception("World Bank fetch failed for %s/%s", country, indicator)
                continue
            for row in rows:
                await wb_repo.upsert(
                    pool,
                    country_code=country,
                    indicator_code=indicator,
                    indicator_label=label,
                    year=row["year"],
                    value=row["value"],
                )
                stored += 1
    return stored

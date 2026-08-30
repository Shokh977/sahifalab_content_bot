"""Drafts a 'finance' pillar post from CBU exchange-rate history or World
Bank indicator comparisons — the data-first pipeline, never a headline.

All numbers (rates, % changes, indicator values) are computed in Python from
stored history before the LLM is called; the model only ever receives
already-computed figures and writes prose around them (see
llm_client.generate_finance_post's prompt, which explicitly forbids it from
computing its own figures).
"""
import asyncpg

from bot.db.repo import drafts as drafts_repo
from bot.db.repo import fx_rates as fx_repo
from bot.db.repo import wb_indicators as wb_repo
from bot.drafting import llm_client


async def draft_fx_change(pool: asyncpg.Pool, currency_code: str, *, days: int = 7) -> int | None:
    change = await fx_repo.get_change(pool, currency_code, days=days)
    if change is None:
        return None

    facts = (
        f"Currency: {change['currency_code']} (Central Bank of Uzbekistan official rate)\n"
        f"Current rate: {change['latest_rate']:,.2f} UZS as of {change['latest_date']}\n"
        f"Rate {change['days']} days ago ({change['past_date']}): {change['past_rate']:,.2f} UZS\n"
        f"Change: {change['pct_change']:+.2f}% ({change['abs_change']:+,.2f} UZS)"
    )
    body_text = await llm_client.generate_finance_post(headline_facts=facts)
    return await drafts_repo.create_text_draft(pool, pillar="finance", body_text=body_text)


async def draft_wb_comparison(pool: asyncpg.Pool, indicator_code: str, indicator_label: str) -> int | None:
    uzb = await wb_repo.get_latest(pool, "UZB", indicator_code)
    kor = await wb_repo.get_latest(pool, "KOR", indicator_code)
    if not uzb or not kor:
        return None

    facts = (
        f"Indicator: {indicator_label} (World Bank Open Data)\n"
        f"Uzbekistan ({uzb['year']}): {float(uzb['value']):,.2f}\n"
        f"South Korea ({kor['year']}): {float(kor['value']):,.2f}"
    )
    body_text = await llm_client.generate_finance_post(headline_facts=facts)
    return await drafts_repo.create_text_draft(pool, pillar="finance", body_text=body_text)

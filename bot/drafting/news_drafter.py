"""Drafts a 'news' pillar post from an ingested RSS item."""
import asyncpg

from bot.db.repo import drafts as drafts_repo
from bot.db.repo import items as items_repo
from bot.drafting import llm_client


async def draft_from_item(pool: asyncpg.Pool, item: asyncpg.Record) -> int:
    body_text = await llm_client.generate_news_post(
        title=item["title"],
        summary=item["summary"] or "",
        url=item["url"],
    )
    draft_id = await drafts_repo.create_text_draft(
        pool,
        pillar="news",
        body_text=body_text,
        source_item_id=item["id"],
    )
    await items_repo.set_status(pool, item["id"], "drafted")
    return draft_id

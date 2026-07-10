"""Drafts a 'tip' pillar post from a topic-bank theme (not the outside web)."""
import asyncpg

from bot.db.repo import drafts as drafts_repo
from bot.db.repo import topics as topics_repo
from bot.drafting import llm_client


async def draft_from_topic(pool: asyncpg.Pool, topic: asyncpg.Record) -> int:
    body_text = await llm_client.generate_tip_post(theme=topic["theme"], notes=topic["notes"])
    draft_id = await drafts_repo.create_text_draft(
        pool,
        pillar="tip",
        body_text=body_text,
        topic_id=topic["id"],
    )
    await topics_repo.mark_used(pool, topic["id"])
    return draft_id

"""Drafts a 'youtube' pillar post from a new channel-upload item."""
import asyncpg

from bot.db.repo import drafts as drafts_repo
from bot.db.repo import items as items_repo
from bot.drafting import llm_client
from bot.ingestion.transcript import get_transcript_text


async def draft_from_item(pool: asyncpg.Pool, item: asyncpg.Record) -> int:
    transcript_snippet = get_transcript_text(item["url"])
    body_text = await llm_client.generate_youtube_post(
        title=item["title"],
        url=item["url"],
        transcript_snippet=transcript_snippet,
    )
    draft_id = await drafts_repo.create_text_draft(
        pool,
        pillar="youtube",
        body_text=body_text,
        source_item_id=item["id"],
    )
    await items_repo.set_status(pool, item["id"], "drafted")
    return draft_id

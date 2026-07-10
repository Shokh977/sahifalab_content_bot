"""Drafts a 'quote' pillar post from a VERIFIED quote-bank row.

Never called with an unverified quote — callers must only pass rows fetched
via bot/db/repo/quotes.py:get_next_unused_verified (verified=true).
"""
import asyncpg

from bot.db.repo import drafts as drafts_repo
from bot.db.repo import quotes as quotes_repo
from bot.drafting import llm_client


async def draft_from_quote(pool: asyncpg.Pool, quote: asyncpg.Record) -> int:
    assert quote["verified"], "quote_drafter must only be called with a verified quote"

    body_text = await llm_client.generate_quote_post(
        quote_text=quote["quote_text"],
        author=quote["author"],
        translation_uz=quote["translation_uz"],
    )
    card_spec = {
        "kind": "quote",
        "quote_text": quote["quote_text"],
        "author": quote["author"],
        "translation_uz": quote["translation_uz"],
    }
    draft_id = await drafts_repo.create_image_card_draft(
        pool,
        pillar="quote",
        body_text=body_text,
        card_spec=card_spec,
        quote_id=quote["id"],
    )
    await quotes_repo.mark_used(pool, quote["id"])
    return draft_id

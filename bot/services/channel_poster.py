"""The ONLY module allowed to call bot.send_message/send_photo/send_poll on
the channel. Every other module may only create `drafts` rows with
status='pending_review' — this is the structural enforcement of "never
auto-post": post_draft() is reachable only from an explicit admin approval
callback (bot/telegram/handlers/approval.py) or a scheduler job acting on a
draft already in approved/scheduled status, both of which require a prior
admin tap.
"""
import json
import logging

import asyncpg
from aiogram import Bot

from bot.config import settings
from bot.cta.rotation import next_cta
from bot.db.repo import drafts as drafts_repo
from bot.db.repo import posts as posts_repo
from bot.images.card_renderer import render_card

logger = logging.getLogger(__name__)

# Pillars that get a rotating CTA appended; poll captions can't carry links usefully.
_CTA_ELIGIBLE_PILLARS = {"news", "tip", "quote", "youtube"}


async def post_draft(bot: Bot, pool: asyncpg.Pool, draft: asyncpg.Record) -> None:
    pillar = draft["pillar"]
    cta_line, utm_campaign = ("", None)
    if pillar in _CTA_ELIGIBLE_PILLARS:
        cta_line, utm_campaign = await next_cta(pool)

    caption = draft["body_text"] or ""
    if cta_line:
        caption = f"{caption}\n\n{cta_line}"

    telegram_message_id = None

    if draft["content_type"] == "poll":
        options = draft["poll_options"]
        if isinstance(options, str):
            options = json.loads(options)
        msg = await bot.send_poll(
            chat_id=settings.CHANNEL_ID,
            question=draft["poll_question"],
            options=options,
            is_anonymous=True,
        )
        telegram_message_id = msg.message_id

    elif draft["content_type"] == "image_card":
        card_spec = draft["card_spec"]
        if isinstance(card_spec, str):
            card_spec = json.loads(card_spec)
        image_bytes = render_card(card_spec)
        from aiogram.types import BufferedInputFile
        photo = BufferedInputFile(image_bytes, filename="card.png")
        msg = await bot.send_photo(chat_id=settings.CHANNEL_ID, photo=photo, caption=caption)
        telegram_message_id = msg.message_id

    else:
        msg = await bot.send_message(chat_id=settings.CHANNEL_ID, text=caption)
        telegram_message_id = msg.message_id

    await drafts_repo.set_status(pool, draft["id"], "posted")
    await posts_repo.log_post(
        pool,
        draft_id=draft["id"],
        pillar=pillar,
        telegram_message_id=telegram_message_id,
        channel_id=settings.CHANNEL_ID,
        utm_campaign=utm_campaign,
    )
    logger.info("Posted draft #%s (pillar=%s) to channel", draft["id"], pillar)

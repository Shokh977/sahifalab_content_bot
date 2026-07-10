"""The ONLY module allowed to call bot.send_message/send_poll on the channel.
Every other module may only create `drafts` rows with status='pending_review' — this is the
structural enforcement of "never auto-post": post_draft() is reachable only from an explicit
admin approval callback (bot/telegram/handlers/approval.py) or a scheduler job acting on a
draft already in approved/scheduled status, both of which require a prior admin tap.

All posts are sent as TEXT-ONLY messages — no images or photos.
Every post includes sahifalab.uz and pillar-specific hashtags.
"""
import json
import logging

import asyncpg
from aiogram import Bot

from bot.config import settings
from bot.db.repo import drafts as drafts_repo
from bot.db.repo import posts as posts_repo

logger = logging.getLogger(__name__)

# Hashtags per pillar
_PILLAR_HASHTAGS = {
    "news": "#kun_yangiligi #sahifalab",
    "tip": "#sahifalab",
    "quote": "#iqtibos #sahifalab",
    "youtube": "#sahifalab",
    "poll": "#sahifalab",
}


async def post_draft(bot: Bot, pool: asyncpg.Pool, draft: asyncpg.Record) -> None:
    pillar = draft["pillar"]
    
    caption = draft["body_text"] or ""
    
    # Append website and hashtags
    hashtags = _PILLAR_HASHTAGS.get(pillar, "#sahifalab")
    footer = f"\n\n🌐 {settings.UTM_BASE_URL}\n{hashtags}"
    caption = f"{caption}{footer}"

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
    else:
        # TEXT-ONLY for all content types: news, tip, quote, youtube, image_card
        # (image_card rows may exist but are sent as text)
        msg = await bot.send_message(chat_id=settings.CHANNEL_ID, text=caption)
        telegram_message_id = msg.message_id

    await drafts_repo.set_status(pool, draft["id"], "posted")
    await posts_repo.log_post(
        pool,
        draft_id=draft["id"],
        pillar=pillar,
        telegram_message_id=telegram_message_id,
        channel_id=settings.CHANNEL_ID,
        utm_campaign=None,
    )
    logger.info("Posted draft #%s (pillar=%s) to channel", draft["id"], pillar)



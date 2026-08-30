"""The ONLY module allowed to call bot.send_message/send_poll on the channel.
Every other module may only create `drafts` rows with status='pending_review' — this is the
structural enforcement of "never auto-post": post_draft() is reachable only from an explicit
admin approval callback (bot/telegram/handlers/approval.py) or a scheduler job acting on a
draft already in approved/scheduled status, both of which require a prior admin tap.

All posts are sent as TEXT-ONLY messages — no images or photos.
Every post includes a link bar to every Sahifalab property plus pillar-specific hashtags.
"""
import html
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
    "finance": "#moliya #sahifalab",
    "news": "#kun_yangiligi #sahifalab",
    "tip": "#sahifalab",
    "quote": "#iqtibos #sahifalab",
    "youtube": "#sahifalab",
    "poll": "#sahifalab",
}

# Every canonical Sahifalab property, appended as clickable links to every post.
_BRAND_LINKS = [
    ("Telegram", "https://t.me/sahifalab1"),
    ("Youtube", "https://youtube.com/@sahifalab"),
    ("Bot", "https://t.me/sahifalab_hub_bot"),
    ("Ilova", "https://play.google.com/store/apps/details?id=com.sahifalab.app"),
    ("sahifalab.uz", "https://sahifalab.uz/"),
]
_LINK_BAR = " · ".join(f'<a href="{url}">{label}</a>' for label, url in _BRAND_LINKS)


async def post_draft(bot: Bot, pool: asyncpg.Pool, draft: asyncpg.Record) -> None:
    pillar = draft["pillar"]

    # HTML parse mode carries the link bar's <a> tags — escape the draft body
    # first so any stray &/</> in generated text can't break the markup or
    # get interpreted as tags.
    caption = html.escape(draft["body_text"] or "")

    hashtags = _PILLAR_HASHTAGS.get(pillar, "#sahifalab")
    footer = f"\n\n🔗 {_LINK_BAR}\n{hashtags}"
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
        msg = await bot.send_message(
            chat_id=settings.CHANNEL_ID,
            text=caption,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
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



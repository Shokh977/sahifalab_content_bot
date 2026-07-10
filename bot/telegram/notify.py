"""Broadcasts a draft preview (with approval buttons) to every admin — used
by scheduler jobs when a new draft is created outside of an interactive
handler (RSS/YouTube ingestion, opportunistic tip/quote drafting).
"""
import json
import logging

import asyncpg
from aiogram import Bot
from aiogram.types import BufferedInputFile

from bot.config import settings
from bot.images.card_renderer import render_card
from bot.telegram.formatting import render_admin_preview
from bot.telegram.keyboards.approval_kb import approval_kb

logger = logging.getLogger(__name__)


async def send_draft_to_admins(bot: Bot, draft: asyncpg.Record) -> None:
    caption = render_admin_preview(draft)
    markup = approval_kb(draft["id"])

    for admin_id in settings.ADMIN_TELEGRAM_IDS:
        try:
            if draft["content_type"] == "image_card":
                card_spec = draft["card_spec"]
                if isinstance(card_spec, str):
                    card_spec = json.loads(card_spec)
                image_bytes = render_card(card_spec)
                photo = BufferedInputFile(image_bytes, filename="card.png")
                await bot.send_photo(chat_id=admin_id, photo=photo, caption=caption)
            else:
                await bot.send_message(chat_id=admin_id, text=caption, reply_markup=markup)
        except Exception:
            logger.exception("Failed to send draft #%s preview to admin %s", draft["id"], admin_id)
            continue

        if draft["content_type"] == "image_card":
            # send_photo above has no room for inline buttons alongside a caption
            # that might exceed Telegram's caption length, so buttons follow separately.
            try:
                await bot.send_message(chat_id=admin_id, text=f"Draft #{draft['id']} — amalni tanlang:", reply_markup=markup)
            except Exception:
                logger.exception("Failed to send approval buttons for draft #%s to admin %s", draft["id"], admin_id)

"""Broadcasts a draft preview (with approval buttons) to every admin — used
by scheduler jobs when a new draft is created outside of an interactive
handler (RSS/YouTube ingestion, opportunistic tip/quote drafting).

All admin previews are sent as TEXT-ONLY messages.
"""
import json
import logging

import asyncpg
from aiogram import Bot

from bot.config import settings
from bot.telegram.formatting import render_admin_preview
from bot.telegram.keyboards.approval_kb import approval_kb

logger = logging.getLogger(__name__)


async def send_draft_to_admins(bot: Bot, draft: asyncpg.Record) -> None:
    caption = render_admin_preview(draft)
    markup = approval_kb(draft["id"])

    for admin_id in settings.ADMIN_TELEGRAM_IDS:
        try:
            # TEXT-ONLY for all draft types: image_card, text, poll
            await bot.send_message(chat_id=admin_id, text=caption, reply_markup=markup)
        except Exception:
            logger.exception("Failed to send draft #%s preview to admin %s", draft["id"], admin_id)


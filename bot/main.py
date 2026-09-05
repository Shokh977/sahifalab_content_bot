"""Bot entry point."""
import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.config import settings
from bot.db.pool import close_pool, get_pool
from bot.scheduler.setup import build_scheduler
from bot.telegram.handlers import (
    approval,
    cancel,
    polls,
    quotes,
    settings_cmds,
    sources,
    start,
    topics,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def _get_storage():
    """Try Redis first; fall back to MemoryStorage if unset/unreachable."""
    if not settings.REDIS_URL:
        logger.info("REDIS_URL not set — using MemoryStorage")
        return MemoryStorage()
    try:
        import redis.asyncio as aioredis
        from aiogram.fsm.storage.redis import RedisStorage
        client = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await client.ping()
        await client.aclose()
        logger.info("Using Redis FSM storage: %s", settings.REDIS_URL)
        return RedisStorage.from_url(settings.REDIS_URL)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — falling back to MemoryStorage", exc)
        return MemoryStorage()


async def main():
    if not settings.BOT_TOKEN:
        logger.error("BOT_TOKEN is not set. Set it in .env and restart.")
        sys.exit(1)
    if not settings.DATABASE_URL:
        logger.error("DATABASE_URL is not set. Set it in .env and restart.")
        sys.exit(1)
    if not settings.CHANNEL_ID:
        logger.warning("CHANNEL_ID is not set — approved posts will fail to send.")
    if not settings.ADMIN_TELEGRAM_IDS:
        logger.warning("ADMIN_TELEGRAM_IDS is not set — nobody will receive draft previews.")
    if not settings.GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY is not set — drafting will fail until it's configured.")

    # Fail fast on a bad DATABASE_URL / unreachable DB before we start polling.
    await get_pool()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher(storage=await _get_storage())

    # Routers — specific/stateful handlers before generic ones.
    dp.include_router(approval.router)
    dp.include_router(sources.router)
    dp.include_router(topics.router)
    dp.include_router(quotes.router)
    dp.include_router(polls.router)
    dp.include_router(settings_cmds.router)
    dp.include_router(cancel.router)
    dp.include_router(start.router)

    scheduler = build_scheduler(bot)
    scheduler.start()

    try:
        logger.info("Starting Sahifalab Content Bot (polling)...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())

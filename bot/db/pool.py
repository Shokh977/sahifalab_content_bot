"""Shared asyncpg connection pool for the content bot."""
import logging
import ssl

import asyncpg

from bot.config import settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


def _build_ssl_context() -> ssl.SSLContext | None:
    """Supabase/any remote Postgres needs TLS; local dev doesn't.

    Mirrors Telegram App/backend/app/db/session.py's _build_connect_args so
    both services connect to the same Supabase instance the same way.
    """
    dsn = settings.DATABASE_URL
    if "localhost" in dsn or "127.0.0.1" in dsn:
        return None
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if not settings.DATABASE_URL:
            raise RuntimeError("DATABASE_URL is not set. Set it in .env and restart.")
        # asyncpg doesn't understand query-string pooler params (pgbouncer, etc.)
        dsn = settings.DATABASE_URL.split("?", 1)[0].strip()
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=1,
            max_size=5,
            ssl=_build_ssl_context(),
        )
        logger.info("Postgres pool created")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Postgres pool closed")

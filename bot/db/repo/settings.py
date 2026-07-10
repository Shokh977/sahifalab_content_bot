"""Queries against public.bot_settings — the runtime-mutable KV store."""
import json

import asyncpg

DEFAULT_MIX_TARGETS = {"news": 0.6, "tip": 0.3, "quote": 0.1}


async def get(pool: asyncpg.Pool, key: str, default=None):
    row = await pool.fetchrow("SELECT value FROM bot_settings WHERE key = $1", key)
    if row is None:
        return default
    return json.loads(row["value"])


async def set(pool: asyncpg.Pool, key: str, value) -> None:
    await pool.execute(
        """
        INSERT INTO bot_settings (key, value, updated_at)
        VALUES ($1, $2, now())
        ON CONFLICT (key) DO UPDATE SET value = $2, updated_at = now()
        """,
        key, json.dumps(value),
    )


async def is_paused(pool: asyncpg.Pool) -> bool:
    return bool(await get(pool, "paused", False))


async def get_mix_targets(pool: asyncpg.Pool) -> dict[str, float]:
    return await get(pool, "mix_targets", DEFAULT_MIX_TARGETS)


async def get_cta_rotation_index(pool: asyncpg.Pool) -> int:
    return int(await get(pool, "cta_rotation_index", 0))

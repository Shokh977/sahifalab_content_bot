"""Queries against public.topics (the tip topic bank)."""
import asyncpg


async def create(pool: asyncpg.Pool, *, theme: str, notes: str | None, created_by: int) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO topics (theme, notes, created_by)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        theme, notes, created_by,
    )
    return row["id"]


async def list_all(pool: asyncpg.Pool, *, active_only: bool = False) -> list[asyncpg.Record]:
    if active_only:
        return await pool.fetch("SELECT * FROM topics WHERE active ORDER BY id")
    return await pool.fetch("SELECT * FROM topics ORDER BY id")


async def set_active(pool: asyncpg.Pool, topic_id: int, active: bool) -> None:
    await pool.execute("UPDATE topics SET active = $2 WHERE id = $1", topic_id, active)


async def get_next_unused(pool: asyncpg.Pool) -> asyncpg.Record | None:
    """Oldest-used (or never-used) active topic, for the opportunistic tip drafter."""
    return await pool.fetchrow(
        """
        SELECT * FROM topics
        WHERE active
        ORDER BY last_used_at ASC NULLS FIRST, id ASC
        LIMIT 1
        """
    )


async def mark_used(pool: asyncpg.Pool, topic_id: int) -> None:
    await pool.execute("UPDATE topics SET last_used_at = now() WHERE id = $1", topic_id)

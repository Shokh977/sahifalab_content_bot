"""Queries against public.sources."""
import asyncpg


async def create(
    pool: asyncpg.Pool,
    *,
    name: str,
    url: str,
    kind: str,
    pillar: str | None,
    created_by: int,
    tag: str | None = None,
    active: bool = False,
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO sources (name, url, kind, pillar, created_by, tag, active)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (url) DO NOTHING
        RETURNING id
        """,
        name, url, kind, pillar, created_by, tag, active,
    )
    return row["id"] if row else None


async def list_all(pool: asyncpg.Pool, *, active_only: bool = False) -> list[asyncpg.Record]:
    if active_only:
        return await pool.fetch("SELECT * FROM sources WHERE active ORDER BY id")
    return await pool.fetch("SELECT * FROM sources ORDER BY id")


async def get(pool: asyncpg.Pool, source_id: int) -> asyncpg.Record | None:
    return await pool.fetchrow("SELECT * FROM sources WHERE id = $1", source_id)


async def set_active(pool: asyncpg.Pool, source_id: int, active: bool) -> None:
    await pool.execute("UPDATE sources SET active = $2 WHERE id = $1", source_id, active)


async def mark_fetched(pool: asyncpg.Pool, source_id: int) -> None:
    await pool.execute(
        "UPDATE sources SET last_fetched_at = now() WHERE id = $1", source_id
    )

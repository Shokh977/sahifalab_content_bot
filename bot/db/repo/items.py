"""Queries against public.items."""
import json

import asyncpg


async def insert_new(
    pool: asyncpg.Pool,
    *,
    source_id: int,
    external_id: str,
    url: str,
    title: str,
    summary: str | None,
    published_at,
    raw_payload: dict,
) -> int | None:
    """Dedups on (source_id, external_id). Returns the new item id, or None if it already existed."""
    row = await pool.fetchrow(
        """
        INSERT INTO items (source_id, external_id, url, title, summary, published_at, raw_payload)
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (source_id, external_id) DO NOTHING
        RETURNING id
        """,
        source_id, external_id, url, title, summary, published_at, json.dumps(raw_payload),
    )
    return row["id"] if row else None


async def list_new(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch("SELECT * FROM items WHERE status = 'new' ORDER BY fetched_at ASC")


async def set_score(pool: asyncpg.Pool, item_id: int, score: float) -> None:
    await pool.execute(
        "UPDATE items SET relevance_score = $2, status = 'scored' WHERE id = $1",
        item_id, score,
    )


async def set_status(pool: asyncpg.Pool, item_id: int, status: str) -> None:
    await pool.execute("UPDATE items SET status = $2 WHERE id = $1", item_id, status)


async def set_full_text(
    pool: asyncpg.Pool, item_id: int, full_text: str | None, extraction_status: str
) -> None:
    await pool.execute(
        "UPDATE items SET full_text = $2, extraction_status = $3 WHERE id = $1",
        item_id, full_text, extraction_status,
    )


async def set_specificity(
    pool: asyncpg.Pool, item_id: int, specificity_score: float, reject_reason: str | None
) -> None:
    await pool.execute(
        "UPDATE items SET specificity_score = $2, reject_reason = $3 WHERE id = $1",
        item_id, specificity_score, reject_reason,
    )

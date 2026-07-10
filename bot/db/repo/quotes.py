"""Queries against public.quotes (the verified-quote bank).

Structural rule: only mark_verified() may ever set verified=true, and it is
only ever called from the /verifyquote admin handler. The AI-facing insert
path (create_pending) always writes verified=false.
"""
import asyncpg


async def create_pending(
    pool: asyncpg.Pool,
    *,
    quote_text: str,
    author: str,
    language: str,
    translation_uz: str | None,
    source_note: str | None,
    added_by: int,
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO quotes (quote_text, author, language, translation_uz, source_note, added_by, verified)
        VALUES ($1, $2, $3, $4, $5, $6, false)
        RETURNING id
        """,
        quote_text, author, language, translation_uz, source_note, added_by,
    )
    return row["id"]


async def mark_verified(pool: asyncpg.Pool, quote_id: int, verified_by: int) -> bool:
    row = await pool.fetchrow(
        """
        UPDATE quotes
        SET verified = true, verified_by = $2, verified_at = now()
        WHERE id = $1 AND verified = false
        RETURNING id
        """,
        quote_id, verified_by,
    )
    return row is not None


async def list_by_status(pool: asyncpg.Pool, *, verified: bool) -> list[asyncpg.Record]:
    return await pool.fetch(
        "SELECT * FROM quotes WHERE verified = $1 ORDER BY id DESC", verified
    )


async def get_next_unused_verified(pool: asyncpg.Pool) -> asyncpg.Record | None:
    return await pool.fetchrow(
        """
        SELECT * FROM quotes
        WHERE verified = true
        ORDER BY last_used_at ASC NULLS FIRST, id ASC
        LIMIT 1
        """
    )


async def mark_used(pool: asyncpg.Pool, quote_id: int) -> None:
    await pool.execute("UPDATE quotes SET last_used_at = now() WHERE id = $1", quote_id)

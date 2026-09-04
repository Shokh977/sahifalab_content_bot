"""Queries against public.curated_facts (the curated fact bank for "5 Savol"'s
O'zbek adabiyoti / Tarix va meros categories — see 004_curated_facts.sql).

Structural rule, mirroring bot/db/repo/quotes.py exactly: only
mark_verified() may ever set verified=true, and it is only ever called from
the /verifyfact admin handler. The AI-facing read path (Telegram
App/backend's daily_quiz_service) only ever selects verified=true AND
active=true rows — it never writes here.
"""
import asyncpg

VALID_CATEGORIES = ("ozbek_adabiyoti", "tarix_meros")


async def create_pending(
    pool: asyncpg.Pool,
    *,
    fact_text: str,
    category: str,
    source: str,
    added_by: int,
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO curated_facts (fact_text, category, source, added_by, verified)
        VALUES ($1, $2, $3, $4, false)
        RETURNING id
        """,
        fact_text, category, source, added_by,
    )
    return row["id"]


async def mark_verified(pool: asyncpg.Pool, fact_id: int, verified_by: int) -> bool:
    row = await pool.fetchrow(
        """
        UPDATE curated_facts
        SET verified = true, verified_by = $2, verified_at = now()
        WHERE id = $1 AND verified = false AND active = true
        RETURNING id
        """,
        fact_id, verified_by,
    )
    return row is not None


async def mark_removed(pool: asyncpg.Pool, fact_id: int) -> bool:
    """Soft delete — no precedent in quotes (no /removequote exists), added
    specifically to back /removefact. Keeps verified_by/verified_at history
    rather than a hard DELETE."""
    row = await pool.fetchrow(
        "UPDATE curated_facts SET active = false WHERE id = $1 AND active = true RETURNING id",
        fact_id,
    )
    return row is not None


async def list_by_status(pool: asyncpg.Pool, *, verified: bool, category: str | None = None) -> list[asyncpg.Record]:
    if category:
        return await pool.fetch(
            "SELECT * FROM curated_facts WHERE verified = $1 AND active = true AND category = $2 ORDER BY id DESC",
            verified, category,
        )
    return await pool.fetch(
        "SELECT * FROM curated_facts WHERE verified = $1 AND active = true ORDER BY id DESC", verified
    )

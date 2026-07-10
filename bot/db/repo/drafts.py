"""Queries against public.drafts — the approval-flow state machine.

Status lifecycle: pending_review -> approved | scheduled | rejected -> posted
Only an explicit admin action (approve/schedule callback) may move a draft
out of pending_review. See bot/services/channel_poster.py for the single
choke point allowed to actually post.
"""
import json

import asyncpg


async def create_text_draft(
    pool: asyncpg.Pool,
    *,
    pillar: str,
    body_text: str,
    source_item_id: int | None = None,
    topic_id: int | None = None,
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO drafts (pillar, content_type, body_text, source_item_id, topic_id)
        VALUES ($1, 'text', $2, $3, $4)
        RETURNING id
        """,
        pillar, body_text, source_item_id, topic_id,
    )
    return row["id"]


async def create_image_card_draft(
    pool: asyncpg.Pool,
    *,
    pillar: str,
    body_text: str,
    card_spec: dict,
    quote_id: int | None = None,
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO drafts (pillar, content_type, body_text, card_spec, quote_id)
        VALUES ($1, 'image_card', $2, $3, $4)
        RETURNING id
        """,
        pillar, body_text, json.dumps(card_spec), quote_id,
    )
    return row["id"]


async def create_poll_draft(
    pool: asyncpg.Pool, *, question: str, options: list[str]
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO drafts (pillar, content_type, poll_question, poll_options)
        VALUES ('poll', 'poll', $1, $2)
        RETURNING id
        """,
        question, json.dumps(options),
    )
    return row["id"]


async def get(pool: asyncpg.Pool, draft_id: int) -> asyncpg.Record | None:
    return await pool.fetchrow("SELECT * FROM drafts WHERE id = $1", draft_id)


async def update_body(pool: asyncpg.Pool, draft_id: int, new_text: str) -> None:
    await pool.execute(
        """
        UPDATE drafts
        SET body_text = $2, edit_count = edit_count + 1
        WHERE id = $1
        """,
        draft_id, new_text,
    )


async def set_status(
    pool: asyncpg.Pool,
    draft_id: int,
    status: str,
    *,
    reviewed_by: int | None = None,
    scheduled_for=None,
    reject_reason: str | None = None,
) -> None:
    await pool.execute(
        """
        UPDATE drafts
        SET status = $2,
            reviewed_by = COALESCE($3, reviewed_by),
            reviewed_at = CASE WHEN $3 IS NOT NULL THEN now() ELSE reviewed_at END,
            scheduled_for = $4,
            reject_reason = COALESCE($5, reject_reason)
        WHERE id = $1
        """,
        draft_id, status, reviewed_by, scheduled_for, reject_reason,
    )


async def list_due_scheduled(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT * FROM drafts
        WHERE status = 'scheduled' AND scheduled_for <= now()
        ORDER BY scheduled_for ASC
        """
    )


async def list_eligible_for_pillar(pool: asyncpg.Pool, pillar: str) -> list[asyncpg.Record]:
    """approved + no explicit schedule => eligible for the weighted-mix queue."""
    return await pool.fetch(
        """
        SELECT * FROM drafts
        WHERE status = 'approved' AND scheduled_for IS NULL AND pillar = $1
        ORDER BY created_at ASC
        """,
        pillar,
    )


async def count_pending_older_than(pool: asyncpg.Pool, hours: int) -> int:
    row = await pool.fetchrow(
        """
        SELECT count(*) AS n FROM drafts
        WHERE status = 'pending_review' AND created_at <= now() - ($1 || ' hours')::interval
        """,
        str(hours),
    )
    return row["n"]


async def count_by_status(pool: asyncpg.Pool) -> dict[str, int]:
    rows = await pool.fetch("SELECT status, count(*) AS n FROM drafts GROUP BY status")
    return {r["status"]: r["n"] for r in rows}


async def recent_quote_draft_within(pool: asyncpg.Pool, hours: float) -> bool:
    row = await pool.fetchrow(
        """
        SELECT 1 FROM drafts
        WHERE pillar = 'quote' AND created_at >= now() - ($1 || ' hours')::interval
        LIMIT 1
        """,
        str(hours),
    )
    return row is not None

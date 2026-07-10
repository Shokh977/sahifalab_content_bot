"""Queries against public.posts — the log of what actually shipped to the channel."""
import asyncpg


async def log_post(
    pool: asyncpg.Pool,
    *,
    draft_id: int,
    pillar: str,
    telegram_message_id: int | None,
    channel_id: int,
    utm_campaign: str | None,
) -> int:
    row = await pool.fetchrow(
        """
        INSERT INTO posts (draft_id, pillar, telegram_message_id, channel_id, utm_campaign)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING id
        """,
        draft_id, pillar, telegram_message_id, channel_id, utm_campaign,
    )
    return row["id"]


async def recent_pillar_counts(pool: asyncpg.Pool, window: int) -> dict[str, int]:
    rows = await pool.fetch(
        """
        SELECT pillar, count(*) AS n FROM (
            SELECT pillar FROM posts
            WHERE pillar IN ('news', 'tip', 'quote')
            ORDER BY posted_at DESC
            LIMIT $1
        ) recent
        GROUP BY pillar
        """,
        window,
    )
    return {r["pillar"]: r["n"] for r in rows}

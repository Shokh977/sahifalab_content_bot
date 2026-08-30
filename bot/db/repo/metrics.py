"""Per-source health metrics — extraction success rate and specificity-gate
rejection rate — surfaced via /listsources so a source quietly producing
unusable items gets caught before it wastes more LLM calls (see
bot/ingestion/extraction.py and bot/ingestion/specificity.py for what
populates items.extraction_status / items.reject_reason).
"""
import asyncpg


async def source_stats(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    return await pool.fetch(
        """
        SELECT
            s.id,
            s.name,
            s.active,
            count(i.id) AS items_total,
            count(i.id) FILTER (WHERE i.extraction_status = 'ok')     AS extraction_ok,
            count(i.id) FILTER (WHERE i.extraction_status = 'failed') AS extraction_failed,
            count(i.id) FILTER (WHERE i.status = 'rejected')          AS rejected,
            count(i.id) FILTER (WHERE i.status = 'drafted')           AS drafted
        FROM sources s
        LEFT JOIN items i ON i.source_id = s.id
        GROUP BY s.id, s.name, s.active
        ORDER BY s.id
        """
    )


async def flagged_sources(
    pool: asyncpg.Pool, *, min_items: int = 20, rejection_threshold: float = 0.6
) -> list[asyncpg.Record]:
    """Sources with >60% rejection rate over at least 20 ingested items —
    the Step 5 hygiene threshold from the sources overhaul brief."""
    rows = await source_stats(pool)
    return [
        r for r in rows
        if r["items_total"] >= min_items and (r["rejected"] / r["items_total"]) > rejection_threshold
    ]

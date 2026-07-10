"""RSS/Atom ingestion for kind='rss' sources."""
import logging
from datetime import datetime, timezone

import asyncpg
import feedparser

from bot.db.repo import items as items_repo

logger = logging.getLogger(__name__)


def _entry_external_id(entry) -> str:
    return entry.get("id") or entry.get("guid") or entry.get("link", "")


def _entry_published_at(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime(*parsed[:6], tzinfo=timezone.utc)


async def fetch_source(pool: asyncpg.Pool, source: asyncpg.Record) -> int:
    """Fetches one RSS source, inserts any new items, returns count of new items."""
    feed = feedparser.parse(source["url"])
    if feed.bozo and not feed.entries:
        logger.warning("RSS parse failed for source %s (%s): %s", source["id"], source["url"], feed.bozo_exception)
        return 0

    new_count = 0
    for entry in feed.entries:
        external_id = _entry_external_id(entry)
        if not external_id:
            continue
        item_id = await items_repo.insert_new(
            pool,
            source_id=source["id"],
            external_id=external_id,
            url=entry.get("link", source["url"]),
            title=entry.get("title", "").strip() or "(no title)",
            summary=entry.get("summary", entry.get("description")),
            published_at=_entry_published_at(entry),
            raw_payload={
                "title": entry.get("title"),
                "summary": entry.get("summary"),
                "link": entry.get("link"),
            },
        )
        if item_id is not None:
            new_count += 1

    return new_count

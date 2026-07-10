"""YouTube channel-uploads ingestion for kind='youtube' sources.

Sources of this kind store their channel uploads RSS URL directly in
sources.url, e.g.
https://www.youtube.com/feeds/videos.xml?channel_id=<CHANNEL_ID>
so this reuses the same feedparser fetch as bot/ingestion/rss.py — YouTube's
uploads feed is itself a plain Atom feed.
"""
import logging

import asyncpg

from bot.ingestion.rss import fetch_source as fetch_rss_source

logger = logging.getLogger(__name__)


async def fetch_source(pool: asyncpg.Pool, source: asyncpg.Record) -> int:
    return await fetch_rss_source(pool, source)

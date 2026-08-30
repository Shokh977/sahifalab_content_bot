"""Full-text article extraction via trafilatura.

RSS summaries are often just a headline-length teaser — or, for aggregator
feeds like Google News search RSS, an empty/boilerplate snippet since the
link is a redirect wrapper rather than the article itself. Drafting from
that alone starves the LLM of real content and produces vague, data-free
posts. This fetches the actual article page and pulls the article body so
drafting has something concrete to work with.

Confirmed live (2026-08-30): a news.google.com/rss/articles/... wrapper link
fetches ~500KB of Google's redirect/consent shell but extracts nothing;
direct publisher URLs (spot.uz, gazeta.uz, psypost.org) extract cleanly.
"""
import asyncio
import logging

import trafilatura
from trafilatura.settings import use_config

logger = logging.getLogger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

_config = use_config()
_config.set("DEFAULT", "USER_AGENTS", _USER_AGENT)
_config.set("DEFAULT", "DOWNLOAD_TIMEOUT", "12")

MAX_CHARS = 6000


def _extract_sync(url: str) -> str | None:
    downloaded = trafilatura.fetch_url(url, config=_config)
    if not downloaded:
        return None
    text = trafilatura.extract(downloaded, config=_config, favor_recall=True)
    if not text:
        return None
    return text[:MAX_CHARS]


async def fetch_full_text(url: str) -> tuple[str | None, str]:
    """Returns (full_text_or_None, extraction_status) where status is
    'ok' or 'failed' (never 'not_attempted' — that's the column default
    for items this was never called on, e.g. YouTube items)."""
    try:
        text = await asyncio.to_thread(_extract_sync, url)
    except Exception as exc:
        logger.warning("Extraction crashed for %s: %s", url, exc)
        return None, "failed"
    return (text, "ok") if text else (None, "failed")

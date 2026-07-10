"""One-off seeding script. Run manually: python -m scripts.seed_sources

Every URL below is a best-guess starting point and MUST be manually opened
in a browser (or `curl`) to confirm it returns valid RSS/Atom XML before you
flip it to active — all rows are inserted with active=false. A couple of
entries are unverified <TODO> placeholders; replace them with a real feed
you've checked yourself.
"""
import asyncio
import logging

from bot.db.pool import close_pool, get_pool
from bot.db.repo import sources as sources_repo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STARTER_SOURCES = [
    {"name": "James Clear", "url": "https://jamesclear.com/feed", "kind": "rss", "pillar": "tip"},
    {"name": "Farnam Street", "url": "https://fs.blog/feed/", "kind": "rss", "pillar": "tip"},
    {"name": "Nir Eyal", "url": "https://www.nirandfar.com/feed/", "kind": "rss", "pillar": "tip"},
    {
        "name": "ScienceDaily — Mind & Brain",
        "url": "https://www.sciencedaily.com/rss/mind_brain.xml",
        "kind": "rss",
        "pillar": "tip",
    },
    {
        "name": "<TODO: verify a finance/behavioral-money blog>",
        "url": "https://www.collabfund.com/blog/?format=rss",
        "kind": "rss",
        "pillar": "news",
    },
    {
        "name": "Korea.net",
        "url": "https://www.korea.net/rss/rss.xml",
        "kind": "rss",
        "pillar": "news",
    },
    {
        "name": "The Korea Herald",
        "url": "http://www.koreaherald.com/rss/index.xml",
        "kind": "rss",
        "pillar": "news",
    },
]


async def main() -> None:
    pool = await get_pool()
    inserted, skipped = 0, 0
    for entry in STARTER_SOURCES:
        source_id = await sources_repo.create(
            pool,
            name=entry["name"],
            url=entry["url"],
            kind=entry["kind"],
            pillar=entry["pillar"],
            created_by=0,
        )
        if source_id is None:
            skipped += 1
            logger.info("Skipped (already exists): %s", entry["name"])
        else:
            inserted += 1
            logger.info("Inserted #%s: %s (inactive)", source_id, entry["name"])

    await close_pool()
    logger.info("Done — %s inserted, %s skipped.", inserted, skipped)
    logger.warning(
        "⚠️  Every source above is INACTIVE. Open each URL yourself to confirm it's a "
        "valid feed, then activate it via /listsources + a direct SQL UPDATE or a future "
        "/activatesource command before the bot will fetch from it."
    )


if __name__ == "__main__":
    asyncio.run(main())

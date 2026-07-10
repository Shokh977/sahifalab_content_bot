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
        "name": "PsyBlog",
        "url": "https://www.spring.org.uk/feed",
        "kind": "rss",
        "pillar": "tip",
    },
    {
        "name": "ScienceDaily — Mind & Brain",
        "url": "https://www.sciencedaily.com/rss/mind_brain.xml",
        "kind": "rss",
        "pillar": "news",
    },
    {
        "name": "Neuroscience News",
        "url": "https://neurosciencenews.com/feed/",
        "kind": "rss",
        "pillar": "news",
    },
    {
        "name": "The Learning Scientists",
        "url": "https://www.learningscientists.org/blog?format=rss",
        "kind": "rss",
        "pillar": "tip",
    },
    {
        "name": "Habits & psychology (Google News)",
        "url": "https://news.google.com/rss/search?q=habit+psychology+research&hl=en-US&gl=US&ceid=US:en",
        "kind": "rss",
        "pillar": "news",
    },
    {
        "name": "Productivity & study (Google News)",
        "url": "https://news.google.com/rss/search?q=productivity+study+tips&hl=en-US&gl=US&ceid=US:en",
        "kind": "rss",
        "pillar": "news",
    },
    {
        "name": "20SomethingFinance",
        "url": "https://feeds.feedburner.com/20somethingfinance",
        "kind": "rss",
        "pillar": "tip",
    },
    {
        "name": "A Wealth of Common Sense",
        "url": "https://awealthofcommonsense.com/feed/",
        "kind": "rss",
        "pillar": "tip",
    },
    {
        "name": "Get Rich Slowly",
        "url": "https://www.getrichslowly.org/feed/",
        "kind": "rss",
        "pillar": "tip",
    },
    {
        "name": "The Penny Hoarder",
        "url": "https://www.thepennyhoarder.com/feed/",
        "kind": "rss",
        "pillar": "tip",
    },
    {
        "name": "Personal finance for young adults (Google News)",
        "url": "https://news.google.com/rss/search?q=personal+finance+young+adults&hl=en-US&gl=US&ceid=US:en",
        "kind": "rss",
        "pillar": "news",
    },
    {
        "name": "Saving & investing for beginners (Google News)",
        "url": "https://news.google.com/rss/search?q=saving+and+investing+beginners&hl=en-US&gl=US&ceid=US:en",
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

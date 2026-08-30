"""One-off seeding script. Run manually: python -m scripts.seed_sources

Sources marked active=True below were verified live during the 2026-08-30
sources overhaul: feed fetched, confirmed valid RSS/Atom with items dated
within the last 24h, and a sample article confirmed to extract full text via
trafilatura (see bot/ingestion/extraction.py). Sources marked active=False
still need that verification (or are known-broken and kept here only as a
documented "don't re-add without fixing X" record) — do not flip them on
without repeating the check yourself, since sites change.

Changes from the original starter list (2026-08-30 overhaul):
  REMOVED  — 3x Google News search-RSS feeds: links resolve to a
             news.google.com redirect/consent shell, not the article.
             Confirmed live: trafilatura fetches ~500KB of that shell and
             extracts zero article text. This was very likely the leading
             cause of vague, data-free posts.
  REMOVED  — The Penny Hoarder: affiliate listicles, low data density.
  ADDED    — Uzbek economy/business feeds (spot.uz, gazeta.uz, kun.uz) and
             two research feeds with genuinely numeric reporting
             (PsyPost, Nature Human Behaviour).
  The finance pillar itself (CBU exchange rates + World Bank indicators) is
  NOT an RSS source — see bot/ingestion/fx_rates.py and
  bot/ingestion/worldbank.py, scheduled daily via job_fetch_finance_data.

Feeds considered and DROPPED because no working RSS could be found even with
a browser User-Agent (checked live 2026-08-30) — do not re-add without
re-verifying first:
  - World Bank Blogs (blogs.worldbank.org/rss and /en/rss both 404; no
    <link rel=alternate> on the blog pages either — looks discontinued)
  - IMF Blog (imf.org blocks non-browser requests with 403 on every path
    tried; unverifiable by automated fetch — try manually from a browser
    session if this is wanted)
  - EurekAlert (eurekalert.org homepage has zero RSS references anywhere;
    RSS appears to have been retired)
  - Korea.net (JS-rendered SPA behind a CloudFront bot-check cookie gate;
    /rss/news.xml resolves to 404 once the gate is passed — no static feed
    discoverable)
  - HRD Korea / EPS announcement pages (eps.go.kr, hrdkorea.or.kr): both
    JS-heavy with no discoverable RSS. Brief suggested a page-change watcher
    as a fallback — not built this session; needs the exact page URL/section
    picked by someone who can browse the real site, not guessed.
"""
import asyncio
import logging

from bot.db.pool import close_pool, get_pool
from bot.db.repo import sources as sources_repo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

STARTER_SOURCES = [
    # ── tip: universal principles, not time-sensitive market commentary ────
    {"name": "James Clear", "url": "https://jamesclear.com/feed", "kind": "rss", "pillar": "tip"},
    {"name": "Farnam Street", "url": "https://fs.blog/feed/", "kind": "rss", "pillar": "tip"},
    {"name": "Nir Eyal", "url": "https://www.nirandfar.com/feed/", "kind": "rss", "pillar": "tip"},
    {"name": "PsyBlog", "url": "https://www.spring.org.uk/feed", "kind": "rss", "pillar": "tip"},
    {
        "name": "The Learning Scientists",
        "url": "https://www.learningscientists.org/blog?format=rss",
        "kind": "rss",
        "pillar": "tip",
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
        # Low priority — brief: drop if its rejection rate proves high once
        # /listsources has real numbers on it.
        "name": "Get Rich Slowly",
        "url": "https://www.getrichslowly.org/feed/",
        "kind": "rss",
        "pillar": "tip",
    },

    # ── news: research with real sample sizes / effect sizes ────────────────
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
        # Verified live 2026-08-30: valid feed, items dated today, sample
        # article extracted 7331 chars of real body text (a PNAS study with
        # concrete numbers) — one of the strongest specificity-gate fits.
        "name": "PsyPost",
        "url": "https://www.psypost.org/feed/",
        "kind": "rss",
        "pillar": "news",
        "active": True,
    },
    {
        # Verified live: valid RSS, dated today. Sample-article extraction
        # FAILED (Nature paywalls full text) — RSS description is usually
        # just the abstract, which may still be enough for a data-first post,
        # but left inactive until someone confirms the abstract text is
        # substantive enough to pass the specificity gate in practice.
        "name": "Nature Human Behaviour",
        "url": "https://www.nature.com/nathumbehav.rss",
        "kind": "rss",
        "pillar": "news",
        "active": False,
    },

    # ── news, finance-tagged: highest audience relevance (Uzbek economy) ────
    {
        # Verified live 2026-08-30: valid feed, items dated today, sample
        # article extracted cleanly (2010 chars). Business/economy focused —
        # the single best addition from this overhaul per the brief.
        "name": "Spot.uz",
        "url": "https://www.spot.uz/ru/rss/",
        "kind": "rss",
        "pillar": "news",
        "tag": "finance",
        "active": True,
    },
    {
        # Verified live: valid feed, dated today, sample article extracted
        # cleanly (1118 chars) — but note this is general Uzbek news, not an
        # economy-specific feed (gazeta.uz has no separate economy RSS).
        "name": "Gazeta.uz",
        "url": "https://www.gazeta.uz/uz/rss/",
        "kind": "rss",
        "pillar": "news",
        "tag": "finance",
        "active": True,
    },
    {
        # Brief's candidate URL (kun.uz/uz/rss) 404s. Real feed found via
        # <link rel="alternate" type="application/rss+xml"> on kun.uz's
        # homepage. No economy-only variant exists — general feed only, but
        # each item carries a <category> tag (e.g. "Iqtisodiyot") if you want
        # to filter client-side later. Verified live: dated today, sample
        # article extracted cleanly (925 chars).
        "name": "Kun.uz",
        "url": "https://kun.uz/news/rss?lang=uz",
        "kind": "rss",
        "pillar": "news",
        "tag": "finance",
        "active": True,
    },

    # ── own content ──────────────────────────────────────────────────────
    {
        # Channel ID resolved from https://www.youtube.com/@SahifaLab (its
        # <link rel="canonical"> tag). Verified live 2026-08-30: feed valid,
        # most recent upload dated 2026-08-16 ("DOLLAR NEGA TINMAY O'SADI?"
        # — already an on-brand finance topic). pillar stays None here;
        # youtube_drafter.py hardcodes pillar='youtube' on the draft itself,
        # outside the finance/tip/news/quote mix rotation.
        "name": "Sahifalab YouTube",
        "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC_UWSL4avVgFAlFcOPaRwyg",
        "kind": "youtube",
        "pillar": None,
        "active": True,
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
            tag=entry.get("tag"),
            active=entry.get("active", False),
        )
        if source_id is None:
            skipped += 1
            logger.info("Skipped (already exists): %s", entry["name"])
        else:
            inserted += 1
            state = "active" if entry.get("active") else "INACTIVE"
            logger.info("Inserted #%s: %s (%s)", source_id, entry["name"], state)

    await close_pool()
    logger.info("Done — %s inserted, %s skipped.", inserted, skipped)
    logger.warning(
        "⚠️  Sources not marked active above still need manual verification — open the "
        "feed URL yourself, confirm recent items and that a sample article's full text "
        "extracts (see bot/ingestion/extraction.py), then activate via /listsources + "
        "UPDATE sources SET active = true WHERE id = <id>;"
    )


if __name__ == "__main__":
    asyncio.run(main())

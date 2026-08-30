-- ══════════════════════════════════════════════════════════════════════════
-- Migration 003 — Insert the newly-verified sources from the 2026-08-30
-- overhaul (Step 3/4). Run in: Supabase Dashboard → SQL Editor → Run
-- (after 001 and 002).
--
-- SQL equivalent of `python -m scripts.seed_sources` for just the NEW rows —
-- the production sources table doesn't match this repo's seed script (it
-- has its own hand-curated rows, e.g. "Research / psychology", "finance"),
-- so this only adds what Step 3/4 actually asked for. ON CONFLICT (url) DO
-- NOTHING makes it safe to re-run.
-- ══════════════════════════════════════════════════════════════════════════

INSERT INTO public.sources (name, url, kind, pillar, tag, active, created_by) VALUES
    -- Verified live 2026-08-30: valid feed, dated today, sample article
    -- extracted 7331 chars of real body text — strong specificity-gate fit.
    ('PsyPost', 'https://www.psypost.org/feed/', 'rss', 'news', NULL, true, 0),

    -- Verified live: valid feed, dated today, sample article extracted
    -- cleanly. Business/economy focused — the single best addition.
    ('Spot.uz', 'https://www.spot.uz/ru/rss/', 'rss', 'news', 'finance', true, 0),

    -- Verified live: valid feed, dated today, sample article extracted
    -- cleanly. General Uzbek news, not economy-only (gazeta.uz has no
    -- separate economy feed).
    ('Gazeta.uz', 'https://www.gazeta.uz/uz/rss/', 'rss', 'news', 'finance', true, 0),

    -- Brief's candidate URL (kun.uz/uz/rss) 404s. Real feed found via
    -- kun.uz's own <link rel="alternate"> tag. Verified live: dated today,
    -- sample article extracted cleanly.
    ('Kun.uz', 'https://kun.uz/news/rss?lang=uz', 'rss', 'news', 'finance', true, 0),

    -- Verified live: valid feed, dated today. Sample-article extraction
    -- FAILED (Nature paywalls full text) — left INACTIVE until someone
    -- confirms the RSS abstract alone clears the specificity gate.
    ('Nature Human Behaviour', 'https://www.nature.com/nathumbehav.rss', 'rss', 'news', NULL, false, 0),

    -- Channel ID resolved from https://www.youtube.com/@SahifaLab. Verified
    -- live: feed valid, latest upload already an on-brand finance topic.
    ('Sahifalab YouTube', 'https://www.youtube.com/feeds/videos.xml?channel_id=UC_UWSL4avVgFAlFcOPaRwyg', 'youtube', NULL, NULL, true, 0)
ON CONFLICT (url) DO NOTHING;

-- ── Verification ─────────────────────────────────────────────────────────
-- SELECT id, name, kind, pillar, tag, active FROM public.sources ORDER BY id;

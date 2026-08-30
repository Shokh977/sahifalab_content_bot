-- ══════════════════════════════════════════════════════════════════════════
-- Migration 002 — Finance pillar + data-first pipeline + source hygiene
-- Run in: Supabase Dashboard → SQL Editor → New Query → Run (after 001)
--
-- Safe to run against either a fresh DB (most clauses no-op) or the DB this
-- bot has been developed against — every DELETE/UPDATE below is scoped by
-- exact URL/value match so it never touches rows it doesn't recognize.
-- ══════════════════════════════════════════════════════════════════════════

-- ── sources: allow the new 'finance' pillar, add a soft topical tag ────────
ALTER TABLE public.sources DROP CONSTRAINT IF EXISTS sources_pillar_check;
ALTER TABLE public.sources ADD CONSTRAINT sources_pillar_check
    CHECK (pillar IS NULL OR pillar IN ('news', 'tip', 'quote', 'finance'));

-- 'tag' is a soft label independent of pillar/mix — e.g. an RSS source can be
-- pillar='news' (so it feeds the news bucket) while tag='finance' marks it as
-- economy-focused for reporting, without pulling it into the finance-pillar
-- mix slot (which is reserved for the CBU/World Bank data-first pipeline).
ALTER TABLE public.sources ADD COLUMN IF NOT EXISTS tag text;

-- ── drafts: allow 'finance' as a pillar value ───────────────────────────────
ALTER TABLE public.drafts DROP CONSTRAINT IF EXISTS drafts_pillar_check;
ALTER TABLE public.drafts ADD CONSTRAINT drafts_pillar_check
    CHECK (pillar IN ('news', 'tip', 'quote', 'finance', 'youtube', 'poll'));

-- ── items: track full-text extraction + the specificity gate outcome ───────
-- (Neither existed before this migration — news_drafter previously drafted
-- from RSS title+summary only, with no extraction step and no gate beyond
-- the brand-relevance score. See bot/ingestion/extraction.py + specificity.py.)
ALTER TABLE public.items ADD COLUMN IF NOT EXISTS full_text text;
ALTER TABLE public.items ADD COLUMN IF NOT EXISTS extraction_status text NOT NULL DEFAULT 'not_attempted';
ALTER TABLE public.items DROP CONSTRAINT IF EXISTS items_extraction_status_check;
ALTER TABLE public.items ADD CONSTRAINT items_extraction_status_check
    CHECK (extraction_status IN ('not_attempted', 'ok', 'failed'));
ALTER TABLE public.items ADD COLUMN IF NOT EXISTS specificity_score numeric;
ALTER TABLE public.items ADD COLUMN IF NOT EXISTS reject_reason text;

CREATE INDEX IF NOT EXISTS idx_items_extraction_status ON public.items(extraction_status);

-- ── fx_rates: daily CBU exchange-rate history ───────────────────────────────
-- Every datapoint is stored with its date so week-over-week / month-over-
-- month changes are computed from real history (bot/db/repo/fx_rates.py),
-- never asked of the LLM.
CREATE TABLE IF NOT EXISTS public.fx_rates (
    id            serial PRIMARY KEY,
    currency_code text NOT NULL,               -- ISO 4217, e.g. 'USD', 'KRW'
    nominal       int NOT NULL DEFAULT 1,       -- CBU quotes some currencies per >1 unit
    rate_uzs      numeric NOT NULL,
    diff_uzs      numeric,                      -- CBU's own day-over-day diff, if provided
    rate_date     date NOT NULL,
    fetched_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT fx_rates_currency_date_uq UNIQUE (currency_code, rate_date)
);
CREATE INDEX IF NOT EXISTS idx_fx_rates_currency_date ON public.fx_rates(currency_code, rate_date DESC);

-- ── wb_indicators: World Bank Open Data observations (UZB + KOR) ───────────
CREATE TABLE IF NOT EXISTS public.wb_indicators (
    id               serial PRIMARY KEY,
    country_code     text NOT NULL,             -- 'UZB' | 'KOR'
    indicator_code   text NOT NULL,              -- e.g. 'FP.CPI.TOTL.ZG'
    indicator_label  text,
    year             int NOT NULL,
    value            numeric,
    fetched_at       timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT wb_indicators_uq UNIQUE (country_code, indicator_code, year)
);
CREATE INDEX IF NOT EXISTS idx_wb_indicators_lookup ON public.wb_indicators(country_code, indicator_code, year DESC);

-- ── bot_settings: new mix default (finance=40, tip=35, news=15, quote=10) ──
-- Only overwrites if the row still holds the OLD default — if an admin has
-- already customized mix_targets, this leaves their value alone; they'll
-- need to run /setmix again to fold finance in.
UPDATE public.bot_settings
SET value = '{"finance":0.40,"tip":0.35,"news":0.15,"quote":0.10}', updated_at = now()
WHERE key = 'mix_targets' AND value = '{"news":0.6,"tip":0.3,"quote":0.1}'::jsonb;

-- ── Remove sources with broken extraction / low data density ───────────────
-- Google News search-wrapper feeds: links resolve to a news.google.com
-- redirect/consent shell, not the article — trafilatura fetches ~500KB of
-- that shell and extracts nothing (verified live during this migration's
-- diagnostic pass). The Penny Hoarder: affiliate listicles, low data density.
DELETE FROM public.sources WHERE url IN (
    'https://news.google.com/rss/search?q=habit+psychology+research&hl=en-US&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=productivity+study+tips&hl=en-US&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=personal+finance+young+adults&hl=en-US&gl=US&ceid=US:en',
    'https://news.google.com/rss/search?q=saving+and+investing+beginners&hl=en-US&gl=US&ceid=US:en',
    'https://www.thepennyhoarder.com/feed/'
);

-- ── Reclassify finance-adjacent tip sources (idempotent no-op if already tip)
UPDATE public.sources SET pillar = 'tip'
WHERE url IN ('https://awealthofcommonsense.com/feed/', 'https://www.getrichslowly.org/feed/');

-- ── Verification ─────────────────────────────────────────────────────────
-- SELECT id, name, pillar, tag, active FROM public.sources ORDER BY id;
-- SELECT key, value FROM public.bot_settings WHERE key = 'mix_targets';
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema='public' AND table_name IN ('fx_rates','wb_indicators');

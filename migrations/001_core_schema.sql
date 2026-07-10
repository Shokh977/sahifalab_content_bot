-- ══════════════════════════════════════════════════════════════════════════
-- Migration 001 — Core schema for the Sahifalab content bot
-- Run in: Supabase Dashboard → SQL Editor → New Query → Run
-- (Same Supabase Postgres instance the FastAPI backend uses — new tables only,
--  no changes to existing backend tables.)
-- ══════════════════════════════════════════════════════════════════════════

-- ── sources: RSS feeds and YouTube channels the bot watches ────────────────
CREATE TABLE IF NOT EXISTS public.sources (
    id                      serial PRIMARY KEY,
    name                    text NOT NULL,
    url                     text NOT NULL UNIQUE,          -- RSS/Atom URL or YouTube uploads-feed URL
    kind                    text NOT NULL DEFAULT 'rss',   -- 'rss' | 'youtube'
    pillar                  text,                          -- hint: 'news' | 'tip' (null for youtube)
    active                  boolean NOT NULL DEFAULT false, -- default OFF until manually verified
    fetch_interval_minutes  int NOT NULL DEFAULT 240,
    last_fetched_at         timestamptz,
    created_by              bigint,                        -- admin telegram id
    created_at              timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT sources_kind_check   CHECK (kind IN ('rss', 'youtube')),
    CONSTRAINT sources_pillar_check CHECK (pillar IS NULL OR pillar IN ('news', 'tip'))
);

-- ── items: raw ingested entries (articles / videos), pre-draft ─────────────
CREATE TABLE IF NOT EXISTS public.items (
    id               serial PRIMARY KEY,
    source_id        int NOT NULL REFERENCES public.sources(id) ON DELETE CASCADE,
    external_id      text NOT NULL,                     -- RSS guid or YouTube video id
    url              text NOT NULL,
    title            text NOT NULL,
    summary          text,
    published_at     timestamptz,
    fetched_at       timestamptz NOT NULL DEFAULT now(),
    relevance_score  numeric,
    status           text NOT NULL DEFAULT 'new',        -- new|scored|drafted|rejected|skipped
    raw_payload      jsonb,                              -- full parsed feed entry, debugging only
    CONSTRAINT items_status_check CHECK (status IN ('new','scored','drafted','rejected','skipped')),
    CONSTRAINT items_source_external_uq UNIQUE (source_id, external_id)
);

-- ── topics: admin-curated tip themes ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.topics (
    id           serial PRIMARY KEY,
    theme        text NOT NULL,
    pillar       text NOT NULL DEFAULT 'tip',
    notes        text,
    active       boolean NOT NULL DEFAULT true,
    last_used_at timestamptz,
    created_by   bigint,
    created_at   timestamptz NOT NULL DEFAULT now()
);

-- ── quotes: verified-quote bank (AI may only insert verified=false rows) ───
CREATE TABLE IF NOT EXISTS public.quotes (
    id             serial PRIMARY KEY,
    quote_text     text NOT NULL,
    author         text NOT NULL,
    language       text NOT NULL DEFAULT 'en',
    translation_uz text,                                -- optional pre-supplied Uzbek translation
    source_note    text,                                -- book/speech reference
    verified       boolean NOT NULL DEFAULT false,       -- ONLY /verifyquote may set true
    added_by       bigint,
    verified_by    bigint,
    verified_at    timestamptz,
    last_used_at   timestamptz,
    created_at     timestamptz NOT NULL DEFAULT now()
);

-- ── drafts: everything awaiting/having gone through admin approval ─────────
CREATE TABLE IF NOT EXISTS public.drafts (
    id              serial PRIMARY KEY,
    pillar          text NOT NULL,                       -- news|tip|quote|youtube|poll
    content_type    text NOT NULL,                        -- text|image_card|poll
    source_item_id  int REFERENCES public.items(id) ON DELETE SET NULL,
    topic_id        int REFERENCES public.topics(id) ON DELETE SET NULL,
    quote_id        int REFERENCES public.quotes(id) ON DELETE SET NULL,
    body_text       text,                                 -- final post text (news/tip/quote/youtube caption)
    card_spec       jsonb,                                -- inputs to re-render Pillow card at post time
    poll_question   text,
    poll_options    jsonb,                                -- list[str]
    status          text NOT NULL DEFAULT 'pending_review', -- pending_review|approved|scheduled|posted|rejected
    scheduled_for   timestamptz,
    reviewed_by     bigint,
    reviewed_at     timestamptz,
    reject_reason   text,
    edit_count      int NOT NULL DEFAULT 0,
    created_at      timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT drafts_pillar_check       CHECK (pillar IN ('news','tip','quote','youtube','poll')),
    CONSTRAINT drafts_content_type_check CHECK (content_type IN ('text','image_card','poll')),
    CONSTRAINT drafts_status_check       CHECK (status IN ('pending_review','approved','scheduled','posted','rejected'))
);

-- ── posts: log of what actually went to the channel ────────────────────────
CREATE TABLE IF NOT EXISTS public.posts (
    id                    serial PRIMARY KEY,
    draft_id              int NOT NULL REFERENCES public.drafts(id) ON DELETE CASCADE,
    pillar                text NOT NULL,
    telegram_message_id   bigint,
    channel_id            bigint NOT NULL,
    utm_campaign          text,
    posted_at             timestamptz NOT NULL DEFAULT now()
);

-- ── bot_settings: runtime-mutable KV (no redeploy needed) ──────────────────
CREATE TABLE IF NOT EXISTS public.bot_settings (
    key         text PRIMARY KEY,
    value       jsonb NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now()
);

-- ── Indexes ──────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_items_source          ON public.items(source_id);
CREATE INDEX IF NOT EXISTS idx_items_status           ON public.items(status);
CREATE INDEX IF NOT EXISTS idx_drafts_status_pillar   ON public.drafts(status, pillar);
CREATE INDEX IF NOT EXISTS idx_drafts_scheduled       ON public.drafts(scheduled_for) WHERE status = 'scheduled';
CREATE INDEX IF NOT EXISTS idx_quotes_verified        ON public.quotes(verified);
CREATE INDEX IF NOT EXISTS idx_posts_posted_at        ON public.posts(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_topics_active          ON public.topics(active);

-- ── Seed runtime-mutable settings ───────────────────────────────────────────
INSERT INTO public.bot_settings (key, value) VALUES
    ('paused',            'false'),
    ('mix_targets',       '{"news":0.6,"tip":0.3,"quote":0.1}'),
    ('cta_rotation_index','0')
ON CONFLICT (key) DO NOTHING;

-- ── Verification ─────────────────────────────────────────────────────────
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema='public' AND table_name IN
--   ('sources','items','topics','quotes','drafts','posts','bot_settings');

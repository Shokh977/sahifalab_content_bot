-- 004_curated_facts.sql — curated fact bank for the "5 Savol" daily quiz's
-- two culturally sensitive categories (O'zbek adabiyoti, Tarix va meros).
--
-- Mirrors 001_core_schema.sql's `quotes` table 1:1 (same verified/
-- verified_by/verified_at structural rule: only mark_verified() may ever
-- set verified=true, and it is only ever called from the /verifyfact admin
-- handler). Consumed directly by Telegram App/backend's daily_quiz_service
-- via raw SQL against this same shared Supabase Postgres instance — see
-- that repo's migrations/096_daily_quiz_verification_upgrade.sql, which
-- adds daily_quiz_questions.curated_fact_id (deliberately NOT a foreign
-- key back to this table, to avoid coupling the two repos' migration
-- ordering).
--
-- `active` has no precedent in `quotes` (which has no delete/remove
-- command at all) — added here specifically to back /removefact, a
-- genuinely new command the brief asks for with no existing pattern to
-- mirror. Soft delete (not a hard DELETE) so verified_by/verified_at
-- history survives a removal, consistent with this table's other
-- audit columns.
CREATE TABLE IF NOT EXISTS public.curated_facts (
    id           serial PRIMARY KEY,
    fact_text    text NOT NULL,
    category     text NOT NULL,                    -- 'ozbek_adabiyoti' | 'tarix_meros'
    source       text NOT NULL,                     -- book/author/established reference
    verified     boolean NOT NULL DEFAULT false,
    active       boolean NOT NULL DEFAULT true,
    added_by     bigint,
    verified_by  bigint,
    verified_at  timestamptz,
    times_used   integer NOT NULL DEFAULT 0,
    last_used_at timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_curated_facts_category_verified
    ON public.curated_facts (category, verified, active);

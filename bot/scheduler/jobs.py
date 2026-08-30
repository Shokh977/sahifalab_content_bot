"""Scheduler job bodies. See bot/scheduler/setup.py for trigger wiring."""
import logging

from aiogram import Bot

from bot.config import settings
from bot.db.pool import get_pool
from bot.db.repo import drafts as drafts_repo
from bot.db.repo import items as items_repo
from bot.db.repo import quotes as quotes_repo
from bot.db.repo import settings as settings_repo
from bot.db.repo import sources as sources_repo
from bot.db.repo import topics as topics_repo
from bot.drafting import finance_drafter, news_drafter, quote_drafter, tip_drafter, youtube_drafter
from bot.ingestion import extraction, fx_rates as fx_ingest, rss, worldbank as wb_ingest, youtube
from bot.ingestion import specificity as specificity_module
from bot.ingestion.relevance import score_item
from bot.scheduler import mix as mix_module
from bot.services.channel_poster import post_draft
from bot.telegram.notify import send_draft_to_admins

logger = logging.getLogger(__name__)


async def job_ingest_and_draft(bot: Bot) -> int:
    """Fetches all active sources, scores new items, drafts anything above
    the relevance threshold, and opportunistically drafts a tip/quote if
    that pillar is currently under its mix target. Returns drafts created.
    """
    pool = await get_pool()
    drafts_created = 0

    sources = await sources_repo.list_all(pool, active_only=True)
    for source in sources:
        try:
            if source["kind"] == "youtube":
                await youtube.fetch_source(pool, source)
            else:
                await rss.fetch_source(pool, source)
            await sources_repo.mark_fetched(pool, source["id"])
        except Exception:
            logger.exception("Ingest failed for source #%s (%s)", source["id"], source["url"])

    new_items = await items_repo.list_new(pool)
    for item in new_items:
        try:
            score = await score_item(item["title"], item["summary"])
            await items_repo.set_score(pool, item["id"], score)
            if score < settings.RELEVANCE_THRESHOLD:
                await items_repo.set_status(pool, item["id"], "skipped")
                await items_repo.set_specificity(pool, item["id"], 0.0, "low_relevance")
                continue

            source = await sources_repo.get(pool, item["source_id"])
            is_youtube = bool(source and source["kind"] == "youtube")

            full_text = None
            if not is_youtube:
                full_text, extraction_status = await extraction.fetch_full_text(item["url"])
                await items_repo.set_full_text(pool, item["id"], full_text, extraction_status)

                specificity_input = full_text or item["summary"] or item["title"]
                spec_score, reject_reason = specificity_module.score(specificity_input)
                await items_repo.set_specificity(pool, item["id"], spec_score, reject_reason)
                if reject_reason:
                    await items_repo.set_status(pool, item["id"], "rejected")
                    continue

            if is_youtube:
                draft_id = await youtube_drafter.draft_from_item(pool, item)
            else:
                draft_id = await news_drafter.draft_from_item(pool, item, full_text=full_text)

            draft = await drafts_repo.get(pool, draft_id)
            await send_draft_to_admins(bot, draft)
            drafts_created += 1
        except Exception:
            logger.exception("Drafting failed for item #%s", item["id"])
            await items_repo.set_status(pool, item["id"], "rejected")

    if await _maybe_draft_tip(bot, pool):
        drafts_created += 1
    if await _maybe_draft_quote(bot, pool):
        drafts_created += 1

    return drafts_created


async def _pillar_under_target(pool, pillar: str) -> bool:
    targets = await mix_module.get_mix_targets(pool)
    actual = await mix_module.get_recent_pillar_counts(pool)
    total = sum(actual.values()) or 1
    return (actual.get(pillar, 0) / total) < targets.get(pillar, 0.0)


async def _maybe_draft_tip(bot: Bot, pool) -> bool:
    if not await _pillar_under_target(pool, "tip"):
        return False
    topic = await topics_repo.get_next_unused(pool)
    if not topic:
        return False
    try:
        draft_id = await tip_drafter.draft_from_topic(pool, topic)
        draft = await drafts_repo.get(pool, draft_id)
        await send_draft_to_admins(bot, draft)
        return True
    except Exception:
        logger.exception("Opportunistic tip drafting failed")
        return False


async def job_fetch_finance_data(bot: Bot) -> None:
    """Daily CBU + World Bank fetch, then an opportunistic finance draft if
    that pillar is under its mix target — mirrors the tip/quote pattern."""
    pool = await get_pool()
    try:
        stored = await fx_ingest.fetch_and_store(pool)
        logger.info("CBU fetch stored %s rate rows", stored)
    except Exception:
        logger.exception("CBU exchange-rate fetch failed")

    try:
        stored = await wb_ingest.fetch_all(pool)
        logger.info("World Bank fetch stored %s observations", stored)
    except Exception:
        logger.exception("World Bank fetch failed")

    if await _pillar_under_target(pool, "finance"):
        await _maybe_draft_finance(bot, pool)


async def _maybe_draft_finance(bot: Bot, pool) -> bool:
    for currency in fx_ingest.PRIORITY_CURRENCIES:
        try:
            draft_id = await finance_drafter.draft_fx_change(pool, currency)
        except Exception:
            logger.exception("Finance drafting failed for currency %s", currency)
            continue
        if draft_id:
            draft = await drafts_repo.get(pool, draft_id)
            await send_draft_to_admins(bot, draft)
            return True
    return False


async def job_flag_bad_sources(bot: Bot) -> None:
    """Alerts admins about any source whose specificity-gate rejection rate
    exceeds 60% over at least 20 ingested items (Step 5 source hygiene)."""
    pool = await get_pool()
    from bot.db.repo import metrics as metrics_repo

    flagged = await metrics_repo.flagged_sources(pool)
    if not flagged:
        return

    lines = [
        f"⚠️ #{r['id']} {r['name']}: {r['rejected']}/{r['items_total']} rad etilgan"
        for r in flagged
    ]
    text = "🚩 Yuqori rad etish darajasidagi manbalar:\n" + "\n".join(lines)
    for admin_id in settings.ADMIN_TELEGRAM_IDS:
        try:
            await bot.send_message(admin_id, text)
        except Exception:
            logger.exception("Failed to send flagged-source alert to admin %s", admin_id)


async def _maybe_draft_quote(bot: Bot, pool) -> bool:
    if not await _pillar_under_target(pool, "quote"):
        return False
    if await drafts_repo.recent_quote_draft_within(pool, settings.QUOTE_DRAFT_COOLDOWN_HOURS):
        return False
    quote = await quotes_repo.get_next_unused_verified(pool)
    if not quote:
        return False
    try:
        draft_id = await quote_drafter.draft_from_quote(pool, quote)
        draft = await drafts_repo.get(pool, draft_id)
        await send_draft_to_admins(bot, draft)
        return True
    except Exception:
        logger.exception("Opportunistic quote drafting failed")
        return False


async def job_post_from_queue(bot: Bot) -> None:
    pool = await get_pool()
    if await settings_repo.is_paused(pool):
        logger.info("Posting is paused — skipping posting-window job")
        return

    draft = await mix_module.pick_next_draft(pool)
    if not draft:
        logger.info("Posting-window job: queue empty, nothing posted")
        return

    try:
        await post_draft(bot, pool, draft)
    except Exception:
        logger.exception("Failed to post draft #%s from posting-window job", draft["id"])


async def job_post_scheduled_due(bot: Bot) -> None:
    pool = await get_pool()
    if await settings_repo.is_paused(pool):
        return

    due = await drafts_repo.list_due_scheduled(pool)
    for draft in due:
        try:
            await post_draft(bot, pool, draft)
        except Exception:
            logger.exception("Failed to post scheduled draft #%s", draft["id"])


async def job_reminder_stale(bot: Bot) -> None:
    pool = await get_pool()
    count = await drafts_repo.count_pending_older_than(pool, 48)
    if count == 0:
        return
    for admin_id in settings.ADMIN_TELEGRAM_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"⏳ {count} ta qoralama 48 soatdan ko'proq vaqtdan beri kutmoqda. /status bilan tekshiring.",
            )
        except Exception:
            logger.exception("Failed to send stale-draft reminder to admin %s", admin_id)

import logging

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.db.pool import get_pool
from bot.db.repo import drafts as drafts_repo
from bot.db.repo import posts as posts_repo
from bot.db.repo import quotes as quotes_repo
from bot.db.repo import settings as settings_repo
from bot.db.repo import sources as sources_repo
from bot.scheduler import mix as mix_module

router = Router()
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_TELEGRAM_IDS


@router.message(Command("status"))
async def cmd_status(message: Message):
    if not _is_admin(message.from_user.id):
        return
    pool = await get_pool()

    paused = await settings_repo.is_paused(pool)
    targets = await mix_module.get_mix_targets(pool)
    actual = await posts_repo.recent_pillar_counts(pool, mix_module.MIX_WINDOW_SIZE)
    total_actual = sum(actual.values()) or 1
    draft_counts = await drafts_repo.count_by_status(pool)
    verified_quotes = len(await quotes_repo.list_by_status(pool, verified=True))
    pending_quotes = len(await quotes_repo.list_by_status(pool, verified=False))
    active_sources = len(await sources_repo.list_all(pool, active_only=True))

    mix_lines = "\n".join(
        f"  {p}: nishon {int(t * 100)}% · joriy {round(actual.get(p, 0) / total_actual * 100)}%"
        for p, t in targets.items()
    )

    status_label = "⏸ TO'XTATILGAN" if paused else "▶️ FAOL"
    text = (
        f"{status_label}\n\n"
        f"<b>Aralashma (oxirgi {mix_module.MIX_WINDOW_SIZE} post):</b>\n{mix_lines}\n\n"
        f"<b>Qoralamalar:</b>\n"
        + "\n".join(f"  {k}: {v}" for k, v in draft_counts.items())
        + f"\n\n<b>Iqtiboslar:</b> {verified_quotes} tasdiqlangan, {pending_quotes} kutmoqda\n"
        f"<b>Faol manbalar:</b> {active_sources}"
    )
    await message.answer(text, parse_mode="HTML")


@router.message(Command("pause"))
async def cmd_pause(message: Message):
    if not _is_admin(message.from_user.id):
        return
    pool = await get_pool()
    await settings_repo.set(pool, "paused", True)
    await message.answer("⏸ Joylash to'xtatildi.")


@router.message(Command("resume"))
async def cmd_resume(message: Message):
    if not _is_admin(message.from_user.id):
        return
    pool = await get_pool()
    await settings_repo.set(pool, "paused", False)
    await message.answer("▶️ Joylash davom ettirildi.")


@router.message(Command("setmix"))
async def cmd_setmix(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Foydalanish: /setmix news=60,tip=30,quote=10")
        return

    try:
        pairs = [p.split("=") for p in parts[1].split(",")]
        raw = {k.strip(): float(v.strip()) for k, v in pairs}
    except ValueError:
        await message.answer("Format xato. Masalan: /setmix news=60,tip=30,quote=10")
        return

    if set(raw.keys()) != {"news", "tip", "quote"} or abs(sum(raw.values()) - 100) > 0.01:
        await message.answer("news, tip, quote barchasi kerak va yig'indisi 100 bo'lishi kerak.")
        return

    targets = {k: v / 100 for k, v in raw.items()}
    pool = await get_pool()
    await settings_repo.set(pool, "mix_targets", targets)
    await message.answer(f"✅ Yangi aralashma: {raw}")


@router.message(Command("draftnow"))
async def cmd_draftnow(message: Message, bot: Bot):
    if not _is_admin(message.from_user.id):
        return
    await message.answer("Ishga tushirilmoqda…")
    from bot.scheduler.jobs import job_ingest_and_draft
    try:
        count = await job_ingest_and_draft(bot)
    except Exception as exc:
        logger.exception("Manual /draftnow failed")
        await message.answer(f"❌ Xato: {exc}")
        return
    await message.answer(f"✅ Tugadi. {count} ta yangi qoralama yaratildi.")

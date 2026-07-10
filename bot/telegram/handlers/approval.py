"""Approve / Schedule / Edit / Reject callbacks — the heart of the approval
flow. Approving/scheduling here (or a scheduler job later acting on a draft
this flow already moved to approved/scheduled) are the only ways a draft can
reach bot/services/channel_poster.post_draft().
"""
import logging
from datetime import datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from dateutil import parser as dateutil_parser

from bot.config import settings
from bot.db.pool import get_pool
from bot.db.repo import drafts as drafts_repo
from bot.services.channel_poster import post_draft
from bot.telegram.formatting import render_admin_preview
from bot.telegram.keyboards.approval_kb import approval_kb, reject_reason_kb, schedule_pick_kb
from bot.telegram.states.admin_states import EditDraftStates, ScheduleDraftStates

router = Router()
logger = logging.getLogger(__name__)


def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_TELEGRAM_IDS


@router.callback_query(F.data.startswith("approve_now:"))
async def cb_approve_now(callback: CallbackQuery, bot: Bot):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    draft_id = int(callback.data.split(":")[1])
    pool = await get_pool()
    draft = await drafts_repo.get(pool, draft_id)
    if not draft or draft["status"] != "pending_review":
        await callback.answer("Bu qoralama endi kutilmayapti.", show_alert=True)
        return

    await drafts_repo.set_status(pool, draft_id, "approved", reviewed_by=callback.from_user.id)
    draft = await drafts_repo.get(pool, draft_id)
    try:
        await post_draft(bot, pool, draft)
    except Exception as exc:
        logger.exception("Failed to post draft #%s", draft_id)
        await callback.answer()
        await callback.message.answer(f"❌ Joylashda xato: {exc}")
        return

    await callback.answer("Joylandi ✅")
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass  # message too old to edit — not worth failing the flow over
    await callback.message.answer(f"✅ Draft #{draft_id} kanalga joylandi.")


@router.callback_query(F.data.startswith("schedule:"))
async def cb_schedule(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    draft_id = int(callback.data.split(":")[1])
    await callback.answer()
    await callback.message.answer("Qachon joylansin?", reply_markup=schedule_pick_kb(draft_id))


@router.callback_query(F.data.startswith("sched_pick:"))
async def cb_schedule_pick(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    _, draft_id_str, code = callback.data.split(":")
    draft_id = int(draft_id_str)
    pool = await get_pool()

    if code == "custom":
        await state.set_state(ScheduleDraftStates.waiting_custom_datetime)
        await state.update_data(draft_id=draft_id)
        await callback.answer()
        await callback.message.answer("Sana/vaqtni kiriting (masalan: 25.12.2026 09:00):")
        return

    now = datetime.now()
    if code == "next_window":
        await drafts_repo.set_status(pool, draft_id, "approved", reviewed_by=callback.from_user.id, scheduled_for=None)
        await callback.answer("Navbatga qo'yildi")
        await callback.message.answer(f"✅ Draft #{draft_id} keyingi joylash oynasida chiqadi.")
        return
    elif code == "plus_3h":
        scheduled_for = now + timedelta(hours=3)
    elif code == "plus_6h":
        scheduled_for = now + timedelta(hours=6)
    elif code == "tomorrow_9am":
        tomorrow = now + timedelta(days=1)
        scheduled_for = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        await callback.answer("Noma'lum tanlov.", show_alert=True)
        return

    await drafts_repo.set_status(
        pool, draft_id, "scheduled", reviewed_by=callback.from_user.id, scheduled_for=scheduled_for
    )
    await callback.answer("Rejalashtirildi")
    await callback.message.answer(f"✅ Draft #{draft_id} {scheduled_for:%d.%m.%Y %H:%M} ga rejalashtirildi.")


@router.message(ScheduleDraftStates.waiting_custom_datetime)
async def schedule_custom_datetime(message: Message, state: FSMContext):
    data = await state.get_data()
    draft_id = data["draft_id"]
    try:
        scheduled_for = dateutil_parser.parse(message.text.strip(), dayfirst=True)
    except (ValueError, OverflowError):
        await message.answer("Sana tushunarsiz. Masalan: 25.12.2026 09:00")
        return

    await state.clear()
    pool = await get_pool()
    await drafts_repo.set_status(
        pool, draft_id, "scheduled", reviewed_by=message.from_user.id, scheduled_for=scheduled_for
    )
    await message.answer(f"✅ Draft #{draft_id} {scheduled_for:%d.%m.%Y %H:%M} ga rejalashtirildi.")


@router.callback_query(F.data.startswith("edit:"))
async def cb_edit(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    draft_id = int(callback.data.split(":")[1])
    await state.set_state(EditDraftStates.waiting_new_text)
    await state.update_data(draft_id=draft_id)
    await callback.answer()
    await callback.message.answer("To'g'irlangan matnni yuboring:")


@router.message(EditDraftStates.waiting_new_text)
async def edit_new_text(message: Message, state: FSMContext):
    data = await state.get_data()
    draft_id = data["draft_id"]
    await state.clear()

    pool = await get_pool()
    await drafts_repo.update_body(pool, draft_id, message.text.strip())
    draft = await drafts_repo.get(pool, draft_id)

    await message.answer(
        render_admin_preview(draft),
        reply_markup=approval_kb(draft_id),
    )


@router.callback_query(F.data.startswith("reject:"))
async def cb_reject(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    draft_id = int(callback.data.split(":")[1])
    await callback.answer()
    await callback.message.answer("Rad etish sababi:", reply_markup=reject_reason_kb(draft_id))


@router.callback_query(F.data.startswith("rej:"))
async def cb_reject_reason(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        await callback.answer()
        return
    _, draft_id_str, reason_key = callback.data.split(":")
    draft_id = int(draft_id_str)

    from bot.telegram.keyboards.approval_kb import REJECT_REASONS
    reason_label = dict(REJECT_REASONS).get(reason_key, reason_key)

    pool = await get_pool()
    await drafts_repo.set_status(
        pool, draft_id, "rejected", reviewed_by=callback.from_user.id, reject_reason=reason_label
    )
    await callback.answer("Rad etildi")
    await callback.message.answer(f"❌ Draft #{draft_id} rad etildi ({reason_label}).")

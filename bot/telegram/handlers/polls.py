from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import settings
from bot.db.pool import get_pool
from bot.db.repo import drafts as drafts_repo
from bot.telegram.formatting import render_admin_preview
from bot.telegram.keyboards.approval_kb import approval_kb
from bot.telegram.states.admin_states import AddPollStates

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_TELEGRAM_IDS


@router.message(Command("addpoll"))
async def cmd_addpoll(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.set_state(AddPollStates.waiting_question)
    await message.answer("So'rovnoma savolini kiriting:")


@router.message(AddPollStates.waiting_question)
async def addpoll_question(message: Message, state: FSMContext):
    await state.update_data(question=message.text.strip())
    await state.set_state(AddPollStates.waiting_options)
    await message.answer("Variantlarni har birini alohida qatorda kiriting (2-10 ta):")


@router.message(AddPollStates.waiting_options)
async def addpoll_options(message: Message, state: FSMContext):
    options = [line.strip() for line in message.text.splitlines() if line.strip()]
    if len(options) < 2 or len(options) > 10:
        await message.answer("2 dan 10 gacha variant kiriting, har birini alohida qatorda.")
        return

    data = await state.get_data()
    await state.clear()

    pool = await get_pool()
    draft_id = await drafts_repo.create_poll_draft(pool, question=data["question"], options=options)
    draft = await drafts_repo.get(pool, draft_id)

    await message.answer(
        render_admin_preview(draft),
        reply_markup=approval_kb(draft_id),
    )

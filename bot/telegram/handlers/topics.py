from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import settings
from bot.db.pool import get_pool
from bot.db.repo import topics as topics_repo
from bot.telegram.states.admin_states import AddTopicStates

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_TELEGRAM_IDS


@router.message(Command("addtopic"))
async def cmd_addtopic(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.set_state(AddTopicStates.waiting_theme)
    await message.answer(
        "Mavzuni kiriting (masalan: 'Namangandagi talaba Koreyaga borish uchun 6 oyda 500k so'm qanday tejaydi'):"
    )


@router.message(AddTopicStates.waiting_theme)
async def addtopic_theme(message: Message, state: FSMContext):
    await state.update_data(theme=message.text.strip())
    await state.set_state(AddTopicStates.waiting_notes)
    await message.answer("Qo'shimcha izoh/burchak (yoki /skip):")


@router.message(AddTopicStates.waiting_notes)
async def addtopic_notes(message: Message, state: FSMContext):
    notes = None if message.text.strip() == "/skip" else message.text.strip()
    data = await state.get_data()
    await state.clear()

    pool = await get_pool()
    topic_id = await topics_repo.create(
        pool, theme=data["theme"], notes=notes, created_by=message.chat.id
    )
    await message.answer(f"✅ Mavzu qo'shildi (#{topic_id}).")


@router.message(Command("listtopics"))
async def cmd_listtopics(message: Message):
    if not _is_admin(message.from_user.id):
        return
    pool = await get_pool()
    rows = await topics_repo.list_all(pool)
    if not rows:
        await message.answer("Mavzular yo'q.")
        return
    lines = []
    for r in rows:
        status = "🟢" if r["active"] else "⚪"
        lines.append(f"{status} #{r['id']} {r['theme']}")
    await message.answer("\n".join(lines))


@router.message(Command("removetopic"))
async def cmd_removetopic(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("Foydalanish: /removetopic <id>")
        return
    topic_id = int(parts[1].strip())
    pool = await get_pool()
    await topics_repo.set_active(pool, topic_id, False)
    await message.answer(f"Mavzu #{topic_id} faolsizlantirildi.")

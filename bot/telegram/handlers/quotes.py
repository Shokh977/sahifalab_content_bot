from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import settings
from bot.db.pool import get_pool
from bot.db.repo import quotes as quotes_repo
from bot.telegram.states.admin_states import AddQuoteStates

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_TELEGRAM_IDS


@router.message(Command("addquote"))
async def cmd_addquote(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.set_state(AddQuoteStates.waiting_quote_text)
    await message.answer("Iqtibos matnini kiriting (asl tilida):")


@router.message(AddQuoteStates.waiting_quote_text)
async def addquote_text(message: Message, state: FSMContext):
    await state.update_data(quote_text=message.text.strip())
    await state.set_state(AddQuoteStates.waiting_author)
    await message.answer("Muallifini kiriting:")


@router.message(AddQuoteStates.waiting_author)
async def addquote_author(message: Message, state: FSMContext):
    await state.update_data(author=message.text.strip())
    await state.set_state(AddQuoteStates.waiting_translation)
    await message.answer("O'zbekcha tarjimasi (yoki /skip — AI o'zi tarjima qiladi):")


@router.message(AddQuoteStates.waiting_translation)
async def addquote_translation(message: Message, state: FSMContext):
    translation = None if message.text.strip() == "/skip" else message.text.strip()
    await state.update_data(translation_uz=translation)
    await state.set_state(AddQuoteStates.waiting_source_note)
    await message.answer("Manba izohi, masalan kitob/nutq nomi (yoki /skip):")


@router.message(AddQuoteStates.waiting_source_note)
async def addquote_source_note(message: Message, state: FSMContext):
    source_note = None if message.text.strip() == "/skip" else message.text.strip()
    data = await state.get_data()
    await state.clear()

    pool = await get_pool()
    quote_id = await quotes_repo.create_pending(
        pool,
        quote_text=data["quote_text"],
        author=data["author"],
        language="en",
        translation_uz=data.get("translation_uz"),
        source_note=source_note,
        added_by=message.chat.id,
    )
    await message.answer(
        f"✅ Iqtibos qo'shildi (#{quote_id}), <b>tekshiruv kutmoqda</b>.\n"
        f"Tasdiqlash uchun: /verifyquote {quote_id}",
        parse_mode="HTML",
    )


@router.message(Command("verifyquote"))
async def cmd_verifyquote(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("Foydalanish: /verifyquote <id>")
        return
    quote_id = int(parts[1].strip())
    pool = await get_pool()
    ok = await quotes_repo.mark_verified(pool, quote_id, verified_by=message.chat.id)
    if ok:
        await message.answer(f"✅ Iqtibos #{quote_id} tasdiqlandi va bankka qo'shildi.")
    else:
        await message.answer(f"⚠️ Iqtibos #{quote_id} topilmadi yoki allaqachon tasdiqlangan.")


@router.callback_query(F.data.startswith("verify_quote:"))
async def cb_verify_quote(callback: CallbackQuery):
    quote_id = int(callback.data.split(":")[1])
    pool = await get_pool()
    ok = await quotes_repo.mark_verified(pool, quote_id, verified_by=callback.from_user.id)
    if ok:
        await callback.answer("Tasdiqlandi ✅")
        await callback.message.edit_text(callback.message.text + "\n\n✅ TASDIQLANDI")
    else:
        await callback.answer("Allaqachon tasdiqlangan yoki topilmadi.", show_alert=True)


@router.message(Command("listquotes"))
async def cmd_listquotes(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    filter_arg = parts[1].strip().lower() if len(parts) > 1 else "pending"
    verified = filter_arg == "verified"

    pool = await get_pool()
    rows = await quotes_repo.list_by_status(pool, verified=verified)
    if not rows:
        await message.answer("Iqtiboslar yo'q.")
        return
    lines = [f"#{r['id']} \"{r['quote_text'][:60]}\" — {r['author']}" for r in rows[:30]]
    await message.answer("\n".join(lines))

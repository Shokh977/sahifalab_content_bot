from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import settings
from bot.db.pool import get_pool
from bot.db.repo import curated_facts as facts_repo
from bot.db.repo.curated_facts import VALID_CATEGORIES
from bot.telegram.states.admin_states import AddFactStates

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_TELEGRAM_IDS


@router.message(Command("addfact"))
async def cmd_addfact(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.set_state(AddFactStates.waiting_category)
    await message.answer(
        "Kategoriyani kiriting (" + " yoki ".join(VALID_CATEGORIES) + "):"
    )


@router.message(AddFactStates.waiting_category)
async def addfact_category(message: Message, state: FSMContext):
    category = message.text.strip().lower()
    if category not in VALID_CATEGORIES:
        await message.answer(
            "Noto'g'ri kategoriya. Quyidagilardan birini kiriting: " + ", ".join(VALID_CATEGORIES)
        )
        return
    await state.update_data(category=category)
    await state.set_state(AddFactStates.waiting_fact_text)
    await message.answer("Fakt matnini kiriting (o'zbek tilida, aniq va tekshirilishi mumkin bo'lgan shaklda):")


@router.message(AddFactStates.waiting_fact_text)
async def addfact_text(message: Message, state: FSMContext):
    await state.update_data(fact_text=message.text.strip())
    await state.set_state(AddFactStates.waiting_source)
    await message.answer("Manba kiriting (kitob, muallif yoki tan olingan manba nomi):")


@router.message(AddFactStates.waiting_source)
async def addfact_source(message: Message, state: FSMContext):
    data = await state.get_data()
    source = message.text.strip()
    await state.clear()

    pool = await get_pool()
    fact_id = await facts_repo.create_pending(
        pool,
        fact_text=data["fact_text"],
        category=data["category"],
        source=source,
        added_by=message.chat.id,
    )
    await message.answer(
        f"✅ Fakt qo'shildi (#{fact_id}), <b>tekshiruv kutmoqda</b>.\n"
        f"Tasdiqlash uchun: /verifyfact {fact_id}",
        parse_mode="HTML",
    )


@router.message(Command("verifyfact"))
async def cmd_verifyfact(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("Foydalanish: /verifyfact <id>")
        return
    fact_id = int(parts[1].strip())
    pool = await get_pool()
    ok = await facts_repo.mark_verified(pool, fact_id, verified_by=message.chat.id)
    if ok:
        await message.answer(f"✅ Fakt #{fact_id} tasdiqlandi va bankka qo'shildi.")
    else:
        await message.answer(f"⚠️ Fakt #{fact_id} topilmadi, allaqachon tasdiqlangan yoki o'chirilgan.")


@router.message(Command("removefact"))
async def cmd_removefact(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("Foydalanish: /removefact <id>")
        return
    fact_id = int(parts[1].strip())
    pool = await get_pool()
    ok = await facts_repo.mark_removed(pool, fact_id)
    if ok:
        await message.answer(f"🗑️ Fakt #{fact_id} o'chirildi (bankdan chiqarildi).")
    else:
        await message.answer(f"⚠️ Fakt #{fact_id} topilmadi yoki allaqachon o'chirilgan.")


@router.message(Command("listfacts"))
async def cmd_listfacts(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split()
    filter_arg = parts[1].strip().lower() if len(parts) > 1 else "pending"
    verified = filter_arg == "verified"
    category = None
    if len(parts) > 2 and parts[2].strip().lower() in VALID_CATEGORIES:
        category = parts[2].strip().lower()

    pool = await get_pool()
    rows = await facts_repo.list_by_status(pool, verified=verified, category=category)
    if not rows:
        await message.answer("Faktlar yo'q.")
        return
    lines = [f"#{r['id']} [{r['category']}] \"{r['fact_text'][:60]}\" — {r['source']}" for r in rows[:30]]
    await message.answer("\n".join(lines))

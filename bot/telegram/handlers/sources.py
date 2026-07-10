from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import settings
from bot.db.pool import get_pool
from bot.db.repo import sources as sources_repo
from bot.telegram.states.admin_states import AddSourceStates

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_TELEGRAM_IDS


@router.message(Command("addsource"))
async def cmd_addsource(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.set_state(AddSourceStates.waiting_name)
    await message.answer("Manba nomini kiriting (masalan: James Clear):")


@router.message(AddSourceStates.waiting_name)
async def addsource_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddSourceStates.waiting_url)
    await message.answer("RSS/Atom (yoki YouTube uploads feed) URL manzilini kiriting:")


@router.message(AddSourceStates.waiting_url)
async def addsource_url(message: Message, state: FSMContext):
    await state.update_data(url=message.text.strip())
    await state.set_state(AddSourceStates.waiting_kind)

    b = InlineKeyboardBuilder()
    b.button(text="RSS", callback_data="src_kind:rss")
    b.button(text="YouTube", callback_data="src_kind:youtube")
    b.adjust(2)
    await message.answer("Manba turi:", reply_markup=b.as_markup())


@router.callback_query(AddSourceStates.waiting_kind, F.data.startswith("src_kind:"))
async def addsource_kind(callback: CallbackQuery, state: FSMContext):
    kind = callback.data.split(":")[1]
    await state.update_data(kind=kind)
    await callback.answer()

    if kind == "youtube":
        await _finish_addsource(callback.message, state, pillar=None)
        return

    b = InlineKeyboardBuilder()
    b.button(text="News", callback_data="src_pillar:news")
    b.button(text="Tip", callback_data="src_pillar:tip")
    b.adjust(2)
    await state.set_state(AddSourceStates.waiting_pillar)
    await callback.message.answer("Ustun (pillar):", reply_markup=b.as_markup())


@router.callback_query(AddSourceStates.waiting_pillar, F.data.startswith("src_pillar:"))
async def addsource_pillar(callback: CallbackQuery, state: FSMContext):
    pillar = callback.data.split(":")[1]
    await callback.answer()
    await _finish_addsource(callback.message, state, pillar=pillar)


async def _finish_addsource(message: Message, state: FSMContext, *, pillar: str | None):
    data = await state.get_data()
    await state.clear()

    pool = await get_pool()
    source_id = await sources_repo.create(
        pool,
        name=data["name"],
        url=data["url"],
        kind=data["kind"],
        pillar=pillar,
        created_by=message.chat.id,
    )
    if source_id is None:
        await message.answer("⚠️ Bu URL allaqachon mavjud.")
        return

    await message.answer(
        f"✅ Manba qo'shildi (#{source_id}), lekin hozircha <b>faol emas</b>.\n"
        f"Feed URL to'g'riligini o'zingiz tekshirib, keyin faollashtiring:\n"
        f"UPDATE sources SET active = true WHERE id = {source_id};",
        parse_mode="HTML",
    )


@router.message(Command("listsources"))
async def cmd_listsources(message: Message):
    if not _is_admin(message.from_user.id):
        return
    pool = await get_pool()
    rows = await sources_repo.list_all(pool)
    if not rows:
        await message.answer("Manbalar yo'q.")
        return
    lines = []
    for r in rows:
        status = "🟢" if r["active"] else "⚪"
        lines.append(f"{status} #{r['id']} {r['name']} ({r['kind']}/{r['pillar'] or '-'}) — {r['url']}")
    await message.answer("\n".join(lines))


@router.message(Command("removesource"))
async def cmd_removesource(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("Foydalanish: /removesource <id>")
        return
    source_id = int(parts[1].strip())
    pool = await get_pool()
    await sources_repo.set_active(pool, source_id, False)
    await message.answer(f"Manba #{source_id} faolsizlantirildi.")

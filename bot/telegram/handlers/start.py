from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings

router = Router()

HELP_TEXT = (
    "<b>Sahifalab Content Bot</b>\n\n"
    "Har bir post kanalga chiqishdan oldin siz tasdiqlashingiz kerak.\n\n"
    "<b>Manbalar:</b>\n"
    "/addsource — yangi RSS/YouTube manba qo'shish\n"
    "/listsources — manbalar ro'yxati\n"
    "/removesource &lt;id&gt; — manbani o'chirish\n\n"
    "<b>Mavzular (tip):</b>\n"
    "/addtopic — yangi mavzu qo'shish\n"
    "/listtopics — mavzular ro'yxati\n"
    "/removetopic &lt;id&gt; — mavzuni o'chirish\n\n"
    "<b>Iqtiboslar:</b>\n"
    "/addquote — yangi iqtibos qo'shish (tekshiruv kutadi)\n"
    "/verifyquote &lt;id&gt; — iqtibosni tasdiqlash\n"
    "/listquotes [pending|verified] — iqtiboslar ro'yxati\n\n"
    "<b>So'rovnoma:</b>\n"
    "/addpoll — yangi so'rovnoma qo'shish\n\n"
    "<b>Boshqaruv:</b>\n"
    "/status — holat va navbat\n"
    "/pause, /resume — joylashni to'xtatish/davom ettirish\n"
    "/setmix news=60,tip=30,quote=10 — nisbatni sozlash\n"
    "/draftnow — navbatdan tashqari darhol qidirish+qoralama\n"
    "/cancel — joriy amalni bekor qilish"
)


def _is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_TELEGRAM_IDS


@router.message(Command("start", "help"))
async def cmd_start(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("Bu bot faqat administratorlar uchun.")
        return
    await message.answer(HELP_TEXT, parse_mode="HTML")

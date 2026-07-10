from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

REJECT_REASONS = [
    ("not_relevant", "Mavzuga mos emas"),
    ("factually_wrong", "Faktik xato"),
    ("off_brand", "Brend ohangiga mos emas"),
    ("duplicate", "Takroriy"),
    ("other", "Boshqa sabab"),
]


def approval_kb(draft_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Tasdiqlash va joylash", callback_data=f"approve_now:{draft_id}")
    b.button(text="🕐 Rejalashtirish", callback_data=f"schedule:{draft_id}")
    b.button(text="✏️ Tahrirlash", callback_data=f"edit:{draft_id}")
    b.button(text="❌ Rad etish", callback_data=f"reject:{draft_id}")
    b.adjust(2, 2)
    return b.as_markup()


def schedule_pick_kb(draft_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="Navbatdagi oyna", callback_data=f"sched_pick:{draft_id}:next_window")
    b.button(text="+3 soat", callback_data=f"sched_pick:{draft_id}:plus_3h")
    b.button(text="+6 soat", callback_data=f"sched_pick:{draft_id}:plus_6h")
    b.button(text="Ertaga 09:00", callback_data=f"sched_pick:{draft_id}:tomorrow_9am")
    b.button(text="Boshqa vaqt…", callback_data=f"sched_pick:{draft_id}:custom")
    b.adjust(2, 2, 1)
    return b.as_markup()


def reject_reason_kb(draft_id: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    for key, label in REJECT_REASONS:
        b.button(text=label, callback_data=f"rej:{draft_id}:{key}")
    b.adjust(1)
    return b.as_markup()

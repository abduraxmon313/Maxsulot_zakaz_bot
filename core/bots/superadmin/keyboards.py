"""Super Admin bot klaviaturalari."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

BTN_SETTINGS = "⚙️ Do'kon sozlamalari"
BTN_ANALYTICS = "📊 Analitika"
BTN_TOGGLE_OPEN = "🔓 Do'kon holati"
BTN_STATUS = "ℹ️ Tizim holati"
BTN_CANCEL = "❌ Bekor qilish"

# Tahrirlanadigan sozlamalar: kalit -> (yorliq, tur). tur: text | int | image
EDITABLE_SETTINGS: list[tuple[str, str, str]] = [
    ("shop_name", "🏪 Do'kon nomi", "text"),
    ("welcome_uz", "👋 Salom xabari (UZ)", "text"),
    ("welcome_ru", "👋 Salom xabari (RU)", "text"),
    ("welcome_en", "👋 Salom xabari (EN)", "text"),
    ("welcome_image", "🖼 Salom rasmi", "image"),
    ("currency", "💱 Valyuta belgisi", "text"),
    ("phone", "☎️ Telefon", "text"),
    ("working_hours", "🕒 Ish vaqti", "text"),
    ("min_order_amount", "🧾 Minimal buyurtma (so'm)", "int"),
    ("delivery_fee", "🚚 Yetkazib berish narxi (so'm)", "int"),
    ("free_delivery_from", "🆓 Bepul yetkazish chegarasi (so'm)", "int"),
    ("primary_color", "🎨 Asosiy rang (#HEX)", "text"),
]

SETTING_LABELS = {key: label for key, label, _ in EDITABLE_SETTINGS}
SETTING_TYPES = {key: typ for key, _, typ in EDITABLE_SETTINGS}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SETTINGS)],
            [KeyboardButton(text=BTN_ANALYTICS), KeyboardButton(text=BTN_TOGGLE_OPEN)],
            [KeyboardButton(text=BTN_STATUS)],
        ],
        resize_keyboard=True,
    )


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_CANCEL)]], resize_keyboard=True)


def settings_inline() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"set:{key}")]
        for key, label, _ in EDITABLE_SETTINGS
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

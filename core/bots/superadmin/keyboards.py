"""Super Admin bot klaviaturalari."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

BTN_SETTINGS = "⚙️ Do'kon sozlamalari"
BTN_ADD_PRODUCT = "➕ Mahsulot"
BTN_PRODUCTS = "📦 Mahsulotlar"
BTN_ADD_CATEGORY = "➕ Kategoriya"
BTN_CATEGORIES = "🗂 Kategoriyalar"
BTN_ANALYTICS = "📊 Analitika"
BTN_TOGGLE_OPEN = "🔓 Do'kon holati"
BTN_SHOP_LOCATION = "📍 Do'kon manzili"
BTN_STATUS = "ℹ️ Tizim holati"
BTN_CANCEL = "❌ Bekor qilish"
BTN_SKIP = "⏭ O'tkazib yuborish"
BTN_SEND_LOCATION = "📍 Lokatsiyani yuborish"

# Tahrirlanadigan sozlamalar: kalit -> (yorliq, tur). tur: text | int | image
EDITABLE_SETTINGS: list[tuple[str, str, str]] = [
    ("shop_name", "🏪 Do'kon nomi", "text"),
    ("shop_image", "🖼 Do'kon rasmi (logo)", "image"),
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
]

SETTING_LABELS = {key: label for key, label, _ in EDITABLE_SETTINGS}
SETTING_TYPES = {key: typ for key, _, typ in EDITABLE_SETTINGS}


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SETTINGS)],
            [KeyboardButton(text=BTN_ADD_PRODUCT), KeyboardButton(text=BTN_PRODUCTS)],
            [KeyboardButton(text=BTN_ADD_CATEGORY), KeyboardButton(text=BTN_CATEGORIES)],
            [KeyboardButton(text=BTN_ANALYTICS), KeyboardButton(text=BTN_TOGGLE_OPEN)],
            [KeyboardButton(text=BTN_SHOP_LOCATION), KeyboardButton(text=BTN_STATUS)],
        ],
        resize_keyboard=True,
    )


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=BTN_CANCEL)]], resize_keyboard=True)


def location_request_menu() -> ReplyKeyboardMarkup:
    """Do'kon lokatsiyasini yuborish uchun (request_location)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SEND_LOCATION, request_location=True)],
            [KeyboardButton(text=BTN_CANCEL)],
        ],
        resize_keyboard=True,
    )


def skip_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_SKIP)], [KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )


def settings_inline() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"set:{key}")]
        for key, label, _ in EDITABLE_SETTINGS
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def categories_inline(categories, prefix: str = "pcat") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{c.emoji} {c.name}", callback_data=f"{prefix}:{c.id}")]
        for c in categories
    ]
    rows.append([InlineKeyboardButton(text="➖ Kategoriyasiz", callback_data=f"{prefix}:0")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def product_card(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Narx", callback_data=f"pedit:price:{product_id}"),
            InlineKeyboardButton(text="📦 Qoldiq", callback_data=f"pedit:stock:{product_id}"),
        ],
        [
            InlineKeyboardButton(text="🔁 Faol/Nofaol", callback_data=f"pedit:toggle:{product_id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"pedit:delete:{product_id}"),
        ],
    ])

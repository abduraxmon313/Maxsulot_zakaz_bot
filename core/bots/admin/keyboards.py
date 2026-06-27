"""Admin bot klaviaturalari."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# Asosiy menyu tugmalari (matni — handlerlarda solishtiriladi).
BTN_NEW_ORDERS = "🆕 Yangi buyurtmalar"
BTN_ADD_PRODUCT = "➕ Mahsulot"
BTN_PRODUCTS = "📦 Mahsulotlar"
BTN_ADD_CATEGORY = "➕ Kategoriya"
BTN_CATEGORIES = "🗂 Kategoriyalar"
BTN_STATS = "📊 Statistika"
BTN_CANCEL = "❌ Bekor qilish"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEW_ORDERS)],
            [KeyboardButton(text=BTN_ADD_PRODUCT), KeyboardButton(text=BTN_PRODUCTS)],
            [KeyboardButton(text=BTN_ADD_CATEGORY), KeyboardButton(text=BTN_CATEGORIES)],
            [KeyboardButton(text=BTN_STATS)],
        ],
        resize_keyboard=True,
    )


def cancel_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_CANCEL)]], resize_keyboard=True
    )


# Buyurtma uchun status amallari — joriy statusga qarab keyingi qadamlar.
_NEXT_BUTTONS = {
    "created": [("✅ Tasdiqlash", "confirmed"), ("❌ Rad etish", "rejected")],
    "confirmed": [("👨‍🍳 Tayyorlash", "preparing"), ("🚗 Yo'lda", "on_way"), ("❌ Bekor", "canceled")],
    "preparing": [("🚗 Yo'lda", "on_way"), ("📍 Yetkazildi", "delivered"), ("❌ Bekor", "canceled")],
    "on_way": [("📍 Yetkazildi", "delivered"), ("❌ Bekor", "canceled")],
    "delivered": [("🎉 Yakunlash", "completed")],
}


def order_actions(order_id: int, status: str) -> InlineKeyboardMarkup | None:
    buttons = _NEXT_BUTTONS.get(status)
    if not buttons:
        return None
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"os:{to}:{order_id}")]
        for label, to in buttons
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

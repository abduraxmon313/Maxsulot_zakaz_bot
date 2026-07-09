"""Admin bot klaviaturalari — faqat buyurtmalar va statistika."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

BTN_NEW_ORDERS = "🆕 Yangi buyurtmalar"
BTN_ALL_ORDERS = "📋 Barcha buyurtmalar"
BTN_STATS = "📊 Statistika"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEW_ORDERS)],
            [KeyboardButton(text=BTN_ALL_ORDERS), KeyboardButton(text=BTN_STATS)],
        ],
        resize_keyboard=True,
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

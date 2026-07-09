"""Sotuv bot klaviaturalari."""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from core.config import WEBAPP_URL
from core.services.i18n import t


def contact_request(lang: str) -> ReplyKeyboardMarkup:
    """Telefon raqamni ulashish tugmasi (onboarding)."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t("btn_share_phone", lang), request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    rows: list[list[KeyboardButton]] = []
    # Mini App tugmasi faqat https URL bo'lganda WebApp sifatida qo'shiladi.
    if WEBAPP_URL.startswith("https://"):
        rows.append([KeyboardButton(text=t("btn_open_shop", lang), web_app=WebAppInfo(url=WEBAPP_URL))])
    else:
        rows.append([KeyboardButton(text=t("btn_open_shop", lang))])
    rows.append([
        KeyboardButton(text=t("btn_my_orders", lang)),
        KeyboardButton(text=t("btn_contact", lang)),
    ])
    rows.append([KeyboardButton(text=t("btn_language", lang))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def language_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇿 O'zbek", callback_data="setlang:uz"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang:en"),
    ]])


def location_request(lang: str) -> ReplyKeyboardMarkup:
    """Yetkazish uchun Telegram native lokatsiya so'rovi (xarita API kerak emas)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t("btn_send_location", lang), request_location=True)],
            [KeyboardButton(text=t("btn_cancel_order", lang))],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def pay_inline(order_token: str, lang: str, paid: bool) -> InlineKeyboardMarkup:
    """To'lash / tasdiqlash tugmasi. paid=True bo'lsa 'To'lash' (avtomatik), aks holda tasdiqlash."""
    label = t("btn_pay_now", lang) if paid else t("btn_confirm_order", lang)
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=f"ordpay:{order_token}")],
        [InlineKeyboardButton(text=t("btn_cancel_order", lang), callback_data="ordcancel")],
    ])


def open_shop_inline(lang: str) -> InlineKeyboardMarkup | None:
    if not WEBAPP_URL.startswith("https://"):
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("btn_open_shop", lang), web_app=WebAppInfo(url=WEBAPP_URL)),
    ]])

"""Sotuv bot handlerlari."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from core.services import order_service, settings_service, user_service
from core.services.i18n import STATUS_LABELS, t
from core.utils import fmt_money
from core.bots.customer.keyboards import language_inline, main_menu

router = Router()


async def _send_welcome(message: Message, lang: str):
    welcome = await settings_service.get(f"welcome_{lang}", "")
    if not welcome:
        welcome = await settings_service.get("welcome_uz", "Xush kelibsiz!")
    image = await settings_service.get("welcome_image", "")
    kb = main_menu(lang)
    if image:
        try:
            await message.answer_photo(photo=image, caption=welcome, reply_markup=kb)
            return
        except Exception:
            pass
    await message.answer(welcome, reply_markup=kb)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession):
    user = await user_service.upsert(
        session,
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name or "",
        username=message.from_user.username,
        language=(message.from_user.language_code or "uz")[:2],
    )
    await _send_welcome(message, user.language)


@router.callback_query(F.data.startswith("setlang:"))
async def cb_set_language(callback: CallbackQuery, session: AsyncSession):
    lang = callback.data.split(":", 1)[1]
    await user_service.set_language(session, callback.from_user.id, lang)
    await callback.answer(t("language_set", lang))
    try:
        await callback.message.delete()
    except Exception:
        pass
    await _send_welcome(callback.message, lang)


def _is_btn(text: str, key: str) -> bool:
    """Tugma matni har qanday tildagi tarjima bilan mos kelishini tekshiradi."""
    from core.services.i18n import TRANSLATIONS
    return text in TRANSLATIONS.get(key, {}).values()


@router.message(F.text)
async def handle_menu(message: Message, session: AsyncSession):
    text = (message.text or "").strip()
    lang = await user_service.get_language(session, message.from_user.id)

    # 🌐 Til
    if _is_btn(text, "btn_language"):
        await message.answer(t("choose_language", lang), reply_markup=language_inline())
        return

    # ☎️ Aloqa
    if _is_btn(text, "btn_contact"):
        phone = await settings_service.get("phone", "")
        hours = await settings_service.get("working_hours", "")
        shop = await settings_service.get("shop_name", "")
        parts = [f"🏪 <b>{shop}</b>"]
        if phone:
            parts.append(f"☎️ {phone}")
        if hours:
            parts.append(f"🕒 {hours}")
        await message.answer("\n".join(parts) or t("btn_contact", lang))
        return

    # 📦 Buyurtmalarim
    if _is_btn(text, "btn_my_orders"):
        orders = await order_service.list_orders(session, telegram_id=message.from_user.id, limit=10)
        if not orders:
            await message.answer(t("no_orders", lang))
            return
        currency = await settings_service.get("currency", "so'm")
        lines = []
        for o in orders:
            label = STATUS_LABELS.get(o.status, o.status)
            lines.append(f"#{o.order_number} — {fmt_money(o.grand_total, currency)} — {label}")
        await message.answer("📦 <b>Buyurtmalaringiz:</b>\n\n" + "\n".join(lines))
        return

    # 🛍 Do'konni ochish (WebApp URL bo'lmasa)
    if _is_btn(text, "btn_open_shop"):
        await _send_welcome(message, lang)
        return

    # Boshqa har qanday matn — menyuni qayta ko'rsatamiz.
    await message.answer("👇", reply_markup=main_menu(lang))

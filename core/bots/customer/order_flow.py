"""
Buyurtma oqimi (Mini App savati → Sotuv bot).

Mini App "Buyurtma berish" tugmasi savatni `Telegram.WebApp.sendData()` orqali
shu botga yuboradi. Bot esa:
  1. Savatni o'qiydi va tekshiradi.
  2. Yetkazib berish bo'lsa — Telegram'ning O'ZINING lokatsiya tugmasi orqali
     joylashuvni so'raydi (hech qanday xarita API kerak emas).
  3. To'lovni so'raydi. To'lov API'si yo'q — "To'lash" bosilsa buyurtma AVTOMATIK
     to'langan deb belgilanadi.
  4. Buyurtmani yaratadi (atomik ombor), adminlarga xabar beradi, mijozga tasdiq.

Bu router `handlers.router` dan OLDIN include qilinadi — shuning uchun holatli
(state) handlerlar umumiy menyu handleridan ustun turadi.
"""
from __future__ import annotations

import json
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from core.services import catalog_service, notify_service, order_service, settings_service, user_service
from core.services.i18n import t
from core.services.order_service import OrderError
from core.utils import fmt_money
from core.bots.customer.keyboards import location_request, main_menu, pay_inline
from core.bots.customer.states import OrderFlow

logger = logging.getLogger(__name__)
router = Router()


async def _currency() -> str:
    return await settings_service.get("currency", "so'm")


def _parse_cart(raw: str) -> dict | None:
    """Mini App yuborgan JSON'ni xavfsiz o'qiydi."""
    try:
        data = json.loads(raw or "{}")
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None

    items = []
    for it in (data.get("items") or []):
        try:
            pid = int(it.get("id"))
            qty = int(it.get("qty", 0))
        except (ValueError, TypeError, AttributeError):
            continue
        if pid > 0 and 0 < qty <= 999:
            items.append({"product_id": pid, "qty": qty})
    if not items:
        return None

    delivery_type = data.get("delivery_type")
    delivery_type = delivery_type if delivery_type in ("delivery", "pickup") else "delivery"
    payment_method = data.get("payment_method")
    payment_method = payment_method if payment_method in ("cash", "card", "online") else "cash"
    note = (str(data.get("note") or "").strip()[:500]) or None

    return {
        "items": items,
        "delivery_type": delivery_type,
        "payment_method": payment_method,
        "note": note,
    }


async def _build_preview(session: AsyncSession, draft: dict, lang: str, currency: str) -> str:
    """Buyurtma xulosasi (tasdiqlash oldidan). Yakuniy narx serverda qayta hisoblanadi."""
    lines = [f"🧾 <b>{t('confirm_order', lang)}</b>", ""]
    items_total = 0
    for it in draft["items"]:
        product = await catalog_service.get_product(session, it["product_id"])
        if not product:
            continue
        line = product.price * it["qty"]
        items_total += line
        lines.append(f"• {product.name} × {it['qty']} = {fmt_money(line, currency)}")

    delivery_fee = 0
    if draft["delivery_type"] == "delivery":
        delivery_fee = await settings_service.get_int("delivery_fee", 0)
        free_from = await settings_service.get_int("free_delivery_from", 0)
        if free_from > 0 and items_total >= free_from:
            delivery_fee = 0

    lines.append("")
    lines.append(f"Mahsulotlar: {fmt_money(items_total, currency)}")
    if draft["delivery_type"] == "delivery":
        lines.append(f"Yetkazish: {fmt_money(delivery_fee, currency)}")
    lines.append(f"<b>Jami: {fmt_money(items_total + delivery_fee, currency)}</b>")
    lines.append("")
    dtype = t("dtype_delivery", lang) if draft["delivery_type"] == "delivery" else t("dtype_pickup", lang)
    lines.append(dtype)
    if draft.get("address"):
        lines.append(f"📍 {draft['address']}")
    pm = t("pay_card", lang) if draft["payment_method"] in ("card", "online") else t("pay_cash", lang)
    lines.append(pm)
    if draft.get("note"):
        lines.append(f"📝 {draft['note']}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
#  1) Mini App'dan savat keldi
# ─────────────────────────────────────────────────────────────
@router.message(F.web_app_data)
async def on_web_app_data(message: Message, state: FSMContext, session: AsyncSession):
    lang = await user_service.get_language(session, message.from_user.id)
    draft = _parse_cart(message.web_app_data.data)
    if not draft:
        await message.answer(t("order_empty", lang), reply_markup=main_menu(lang))
        return

    # Do'kon ochiqligini tekshiramiz.
    if not await settings_service.get_bool("is_open", True):
        hours = await settings_service.get("working_hours", "")
        await message.answer(t("shop_closed", lang, hours=hours), reply_markup=main_menu(lang))
        return

    # Telefon raqami majburiy (onboarding'da olingan bo'lishi kerak).
    user = await user_service.get_by_telegram_id(session, message.from_user.id)
    if not user or not user.phone:
        await message.answer(t("order_need_phone", lang), reply_markup=main_menu(lang))
        return

    await state.update_data(draft=draft)

    if draft["delivery_type"] == "delivery":
        await state.set_state(OrderFlow.location)
        await message.answer(t("ask_location", lang), reply_markup=location_request(lang))
    else:
        await _go_to_payment(message, state, session, lang)


async def _go_to_payment(message: Message, state: FSMContext, session: AsyncSession, lang: str):
    data = await state.get_data()
    draft = data.get("draft") or {}
    currency = await _currency()
    preview = await _build_preview(session, draft, lang, currency)
    paid = draft.get("payment_method") in ("card", "online")
    await state.set_state(OrderFlow.payment)
    await message.answer(preview, reply_markup=pay_inline("go", lang, paid))


# ─────────────────────────────────────────────────────────────
#  2) Lokatsiya bosqichi (yetkazib berish)
# ─────────────────────────────────────────────────────────────
@router.message(OrderFlow.location, F.location)
async def location_received(message: Message, state: FSMContext, session: AsyncSession):
    lang = await user_service.get_language(session, message.from_user.id)
    data = await state.get_data()
    draft = data.get("draft") or {}
    draft["lat"] = message.location.latitude
    draft["lng"] = message.location.longitude
    draft["address"] = "📍 Lokatsiya (xaritada yuborilgan)"
    await state.update_data(draft=draft)
    await message.answer(t("location_saved", lang), reply_markup=main_menu(lang))
    await _go_to_payment(message, state, session, lang)


@router.message(OrderFlow.location, F.text)
async def location_text(message: Message, state: FSMContext, session: AsyncSession):
    lang = await user_service.get_language(session, message.from_user.id)
    text = (message.text or "").strip()
    # Bekor qilish tugmasi.
    if text == t("btn_cancel_order", lang):
        await state.clear()
        await message.answer(t("order_canceled_msg", lang), reply_markup=main_menu(lang))
        return
    # Aks holda — matnli manzil sifatida qabul qilamiz.
    data = await state.get_data()
    draft = data.get("draft") or {}
    draft["address"] = text[:512]
    await state.update_data(draft=draft)
    await _go_to_payment(message, state, session, lang)


# ─────────────────────────────────────────────────────────────
#  3) To'lov / tasdiqlash bosqichi
# ─────────────────────────────────────────────────────────────
@router.callback_query(F.data == "ordcancel")
async def order_cancel(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    lang = await user_service.get_language(session, callback.from_user.id)
    await state.clear()
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer(t("order_canceled_msg", lang), reply_markup=main_menu(lang))
    await callback.answer()


@router.callback_query(OrderFlow.payment, F.data.startswith("ordpay:"))
async def order_pay(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    lang = await user_service.get_language(session, callback.from_user.id)
    data = await state.get_data()
    draft = data.get("draft") or {}
    if not draft.get("items"):
        await state.clear()
        await callback.answer(t("order_empty", lang), show_alert=True)
        return

    payment_method = draft.get("payment_method", "cash")
    is_paid = payment_method in ("card", "online")

    # Tugmani o'chiramiz (ikki marta bosishning oldini olamiz).
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    if is_paid:
        await callback.answer(t("paying", lang))
    else:
        await callback.answer()

    user = await user_service.get_by_telegram_id(session, callback.from_user.id)
    customer_name = (user.full_name if user else "") or (callback.from_user.full_name or "Mijoz")
    phone = user.phone if user else None

    try:
        order = await order_service.create_order(
            session,
            telegram_id=callback.from_user.id,
            customer_name=customer_name,
            items=draft["items"],
            delivery_type=draft.get("delivery_type", "delivery"),
            address=draft.get("address"),
            lat=draft.get("lat"),
            lng=draft.get("lng"),
            phone=phone,
            payment_method=payment_method,
            is_paid=is_paid,
            note=draft.get("note"),
        )
    except OrderError as e:
        await state.clear()
        await callback.message.answer(f"❌ {e}", reply_markup=main_menu(lang))
        return
    except Exception as e:
        logger.exception("Buyurtma yaratishda xato: %s", e)
        await state.clear()
        await callback.message.answer("❌ Buyurtma yaratib bo'lmadi. Qayta urinib ko'ring.", reply_markup=main_menu(lang))
        return

    await state.clear()
    currency = await _currency()

    # To'lov "muvaffaqiyatli" (avtomatik) — mijozga bildiramiz.
    if is_paid:
        await callback.message.answer(t("paid_ok", lang))

    await callback.message.answer(
        t(
            "order_placed", lang,
            order_number=t("order_number", lang),
            number=order.order_number,
            total=fmt_money(order.grand_total, currency),
        ),
        reply_markup=main_menu(lang),
    )

    # Adminlarga bildirishnoma (xato bo'lsa ham buyurtma saqlanadi).
    try:
        from core.bots.admin.notify import notify_new_order
        await notify_new_order(order, currency)
    except Exception as e:
        logger.warning("Admin bildirishnomasi yuborilmadi: %s", e)

"""
Admin bot handlerlari — FAQAT buyurtmalar.

Admin: yangi buyurtmalarni ko'radi, tasdiqlaydi/rad etadi, statusni boshqaradi
va statistikani ko'radi. Mahsulot/kategoriya qo'shish — Super Admin botda.
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import BaseFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from core.services import (
    admin_service,
    catalog_service,
    notify_service,
    order_service,
    settings_service,
    user_service,
)
from core.services.i18n import STATUS_LABELS, t
from core.services.order_service import OrderError
from core.utils import fmt_money, order_summary_text
from core.bots.admin import keyboards as kb
from core.bots.admin.states import CancelOrder

logger = logging.getLogger(__name__)
router = Router()


class IsAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        user = getattr(event, "from_user", None)
        if not user:
            return False
        # Env + DB (bot orqali qo'shilgan adminlar) — kesh TTL bilan yangilanadi.
        await admin_service.ensure_loaded()
        return admin_service.is_admin_sync(user.id)


router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def _currency() -> str:
    return await settings_service.get("currency", "so'm")


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👨‍💼 <b>Admin panel</b>\n"
        "Bu yerda buyurtmalarni qabul qilasiz, tasdiqlaysiz va statusini boshqarasiz.",
        reply_markup=kb.main_menu(),
    )


@router.message(F.text == kb.BTN_NEW_ORDERS)
async def show_new_orders(message: Message, session: AsyncSession):
    currency = await _currency()
    active = ["created", "confirmed", "preparing", "on_way"]
    shown = 0
    for st in active:
        orders = await order_service.list_orders(session, status=st, limit=10)
        for o in orders:
            await message.answer(
                order_summary_text(o, currency, for_admin=True),
                reply_markup=kb.order_actions(o.id, o.status),
            )
            shown += 1
    if shown == 0:
        await message.answer("Faol buyurtmalar yo'q ✅")


@router.message(F.text == kb.BTN_ALL_ORDERS)
async def show_all_orders(message: Message, session: AsyncSession):
    orders = await order_service.list_orders(session, limit=15)
    if not orders:
        await message.answer("Buyurtmalar yo'q.")
        return
    currency = await _currency()
    lines = ["📋 <b>So'nggi buyurtmalar:</b>\n"]
    for o in orders:
        label = STATUS_LABELS.get(o.status, o.status)
        lines.append(f"#{o.order_number} — {fmt_money(o.grand_total, currency)} — {label}")
    await message.answer("\n".join(lines))


async def _apply_status(session, order, to_status, actor_id, reason=None) -> str | None:
    """Statusni o'zgartiradi va mijozga bildiradi. Xato bo'lsa xato matnini qaytaradi."""
    try:
        await order_service.change_status(session, order, to_status, actor_id=actor_id, note=reason)
    except OrderError as e:
        return str(e)

    # Mijozga avtomatik xabar (uning tilida) — bekor/rad bo'lsa sabab bilan.
    lang = await user_service.get_language(session, order.user_id)
    status_text = t(f"status_{order.status}", lang)
    msg = f"{status_text}\n{t('order_number', lang)} #{order.order_number}"
    if reason and order.status in ("canceled", "rejected"):
        msg += f"\n📝 {t('cancel_reason_label', lang)}: {reason}"
    await notify_service.notify_customer(order.user_id, msg)
    return None


@router.callback_query(F.data.startswith("os:"))
async def order_status_change(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    _, to_status, order_id = callback.data.split(":")
    order = await order_service.get_order(session, int(order_id))
    if not order:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return

    # Bekor qilish / rad etish → avval sabab so'raymiz.
    if to_status in ("canceled", "rejected"):
        await state.set_state(CancelOrder.reason)
        await state.update_data(order_id=order.id, to_status=to_status)
        await callback.message.answer(
            "❓ Bekor qilish sababini yozing (mijozga yuboriladi).\n"
            "Yoki «⏭ Sababsiz bekor qilish» tugmasini bosing.",
            reply_markup=kb.cancel_reason_menu(),
        )
        await callback.answer()
        return

    err = await _apply_status(session, order, to_status, callback.from_user.id)
    if err:
        await callback.answer(err, show_alert=True)
        return
    currency = await _currency()
    try:
        await callback.message.edit_text(
            order_summary_text(order, currency, for_admin=True)
            + f"\n\n<b>Holat: {STATUS_LABELS.get(order.status, order.status)}</b>",
            reply_markup=kb.order_actions(order.id, order.status),
        )
    except Exception:
        pass
    await callback.answer("✅ Holat yangilandi")


@router.message(CancelOrder.reason, F.text)
async def cancel_reason_received(message: Message, session: AsyncSession, state: FSMContext):
    text = (message.text or "").strip()
    if text == kb.BTN_CANCEL_ABORT:
        await state.clear()
        await message.answer("Bekor qilish to'xtatildi.", reply_markup=kb.main_menu())
        return

    data = await state.get_data()
    await state.clear()
    order_id = data.get("order_id")
    to_status = data.get("to_status", "canceled")
    order = await order_service.get_order(session, int(order_id)) if order_id else None
    if not order:
        await message.answer("Buyurtma topilmadi.", reply_markup=kb.main_menu())
        return

    reason = None if text == kb.BTN_CANCEL_SKIP else text[:255]
    err = await _apply_status(session, order, to_status, message.from_user.id, reason=reason)
    if err:
        await message.answer(f"❗️ {err}", reply_markup=kb.main_menu())
        return
    label = STATUS_LABELS.get(to_status, to_status)
    suffix = f"\n📝 Sabab: {reason}" if reason else ""
    await message.answer(f"✅ Buyurtma #{order.order_number} — {label}{suffix}", reply_markup=kb.main_menu())


@router.message(F.text == kb.BTN_STATS)
async def show_stats(message: Message, session: AsyncSession):
    s = await order_service.stats_summary(session)
    currency = await _currency()
    products = await catalog_service.count_active_products(session)
    await message.answer(
        "📊 <b>Statistika</b>\n\n"
        f"🆕 Yangi (kutilmoqda): {s['pending']}\n"
        f"📅 Bugungi buyurtmalar: {s['today_orders']}\n"
        f"📦 Jami buyurtmalar: {s['total_orders']}\n"
        f"💰 Tushum (yetkazilgan): {fmt_money(s['revenue'], currency)}\n"
        f"🛍 Faol mahsulotlar: {products}"
    )

"""
Admin bot handlerlari — FAQAT buyurtmalar.

Admin: yangi buyurtmalarni ko'radi, tasdiqlaydi/rad etadi, statusni boshqaradi
va statistikani ko'radi. Mahsulot/kategoriya qo'shish — Super Admin botda.
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import BaseFilter, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import is_admin
from core.services import (
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

logger = logging.getLogger(__name__)
router = Router()


class IsAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and is_admin(user.id))


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


@router.callback_query(F.data.startswith("os:"))
async def order_status_change(callback: CallbackQuery, session: AsyncSession):
    _, to_status, order_id = callback.data.split(":")
    order = await order_service.get_order(session, int(order_id))
    if not order:
        await callback.answer("Buyurtma topilmadi.", show_alert=True)
        return
    try:
        await order_service.change_status(session, order, to_status, actor_id=callback.from_user.id)
    except OrderError as e:
        await callback.answer(str(e), show_alert=True)
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

    # Mijozga avtomatik xabar (uning tilida).
    lang = await user_service.get_language(session, order.user_id)
    status_text = t(f"status_{order.status}", lang)
    await notify_service.notify_customer(
        order.user_id,
        f"{status_text}\n{t('order_number', lang)} #{order.order_number}",
    )


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

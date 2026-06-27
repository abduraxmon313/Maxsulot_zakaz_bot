"""Admin bot handlerlari: buyurtmalar, mahsulotlar, kategoriyalar, statistika."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command, CommandStart
from aiogram.fsm.context import FSMContext
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
from core.bots.admin.states import AddCategory, AddProduct, EditPrice, EditStock

logger = logging.getLogger(__name__)
router = Router()

BTN_SKIP = "⏭ O'tkazib yuborish"


class IsAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and is_admin(user.id))


# Faqat adminlar — barcha message/callback handlerlariga filtr.
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def _currency() -> str:
    return await settings_service.get("currency", "so'm")


# ─────────────────────────────────────────────────────────────
#  Start / Menyu
# ─────────────────────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👨‍💼 <b>Admin panel</b>\nBuyurtmalar va katalogni boshqaring.",
        reply_markup=kb.main_menu(),
    )


@router.message(F.text == kb.BTN_CANCEL)
async def cancel_any(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=kb.main_menu())


# ─────────────────────────────────────────────────────────────
#  Buyurtmalar
# ─────────────────────────────────────────────────────────────
@router.message(F.text == kb.BTN_NEW_ORDERS)
async def show_orders(message: Message, session: AsyncSession):
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
    # Admin xabarini yangilaymiz.
    try:
        await callback.message.edit_text(
            order_summary_text(order, currency, for_admin=True)
            + f"\n\n<b>Holat: {STATUS_LABELS.get(order.status, order.status)}</b>",
            reply_markup=kb.order_actions(order.id, order.status),
        )
    except Exception:
        pass
    await callback.answer("✅ Holat yangilandi")

    # Mijozga xabar.
    lang = await user_service.get_language(session, order.user_id)
    status_text = t(f"status_{order.status}", lang)
    await notify_service.notify_customer(
        order.user_id,
        f"{status_text}\n{t('order_number', lang)} #{order.order_number}",
    )


# ─────────────────────────────────────────────────────────────
#  Mahsulot qo'shish (FSM)
# ─────────────────────────────────────────────────────────────
@router.message(F.text == kb.BTN_ADD_PRODUCT)
async def add_product_start(message: Message, state: FSMContext):
    await state.set_state(AddProduct.name)
    await message.answer("Mahsulot nomini kiriting:", reply_markup=kb.cancel_menu())


@router.message(AddProduct.name, F.text)
async def add_product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProduct.price)
    await message.answer("Narxini kiriting (faqat raqam, so'mda):")


@router.message(AddProduct.price, F.text)
async def add_product_price(message: Message, state: FSMContext):
    digits = "".join(ch for ch in message.text if ch.isdigit())
    if not digits:
        await message.answer("❗️ Narx faqat raqam bo'lsin. Qayta kiriting:")
        return
    await state.update_data(price=int(digits))
    await state.set_state(AddProduct.stock)
    await message.answer("Ombordagi qoldiq (soni)ni kiriting:")


@router.message(AddProduct.stock, F.text)
async def add_product_stock(message: Message, state: FSMContext, session: AsyncSession):
    digits = "".join(ch for ch in message.text if ch.isdigit())
    if not digits:
        await message.answer("❗️ Qoldiq faqat raqam bo'lsin. Qayta kiriting:")
        return
    await state.update_data(stock=int(digits))
    cats = await catalog_service.list_categories(session)
    await state.set_state(AddProduct.category)
    if cats:
        await message.answer("Kategoriyani tanlang:", reply_markup=kb.categories_inline(cats))
    else:
        await state.update_data(category_id=None)
        await state.set_state(AddProduct.photo)
        await message.answer(
            "Mahsulot rasmini yuboring yoki o'tkazib yuboring:",
            reply_markup=_skip_kb(),
        )


@router.callback_query(AddProduct.category, F.data.startswith("pcat:"))
async def add_product_category(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=cat_id or None)
    await state.set_state(AddProduct.photo)
    await callback.message.answer(
        "Mahsulot rasmini yuboring yoki o'tkazib yuboring:", reply_markup=_skip_kb()
    )
    await callback.answer()


@router.message(AddProduct.photo, F.photo)
async def add_product_photo(message: Message, state: FSMContext, session: AsyncSession):
    file_id = message.photo[-1].file_id
    await _finish_product(message, state, session, image_file_id=file_id)


@router.message(AddProduct.photo, F.text)
async def add_product_photo_skip(message: Message, state: FSMContext, session: AsyncSession):
    await _finish_product(message, state, session, image_file_id=None)


async def _finish_product(message, state, session, image_file_id):
    data = await state.get_data()
    product = await catalog_service.create_product(
        session,
        name=data["name"],
        price=data["price"],
        category_id=data.get("category_id"),
        stock=data.get("stock", 0),
        image_file_id=image_file_id,
    )
    await state.clear()
    currency = await _currency()
    await message.answer(
        f"✅ Mahsulot qo'shildi:\n<b>{product.name}</b> — {fmt_money(product.price, currency)}\n"
        f"Qoldiq: {product.stock}",
        reply_markup=kb.main_menu(),
    )


def _skip_kb():
    from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_SKIP)], [KeyboardButton(text=kb.BTN_CANCEL)]],
        resize_keyboard=True,
    )


# ─────────────────────────────────────────────────────────────
#  Mahsulotlar ro'yxati va tahrirlash
# ─────────────────────────────────────────────────────────────
@router.message(F.text == kb.BTN_PRODUCTS)
async def list_products(message: Message, session: AsyncSession):
    products = await catalog_service.list_products(session, only_active=False, limit=40)
    if not products:
        await message.answer("Mahsulotlar yo'q. ➕ Mahsulot tugmasi orqali qo'shing.")
        return
    currency = await _currency()
    for p in products:
        flag = "🟢" if (p.is_active and p.deleted_at is None) else "🔴"
        await message.answer(
            f"{flag} <b>{p.name}</b>\n💰 {fmt_money(p.price, currency)} | 📦 {p.stock} dona",
            reply_markup=kb.product_card(p.id),
        )


@router.callback_query(F.data.startswith("pedit:"))
async def product_edit(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    _, action, pid = callback.data.split(":")
    pid = int(pid)
    product = await catalog_service.get_product(session, pid)
    if not product:
        await callback.answer("Topilmadi.", show_alert=True)
        return

    if action == "price":
        await state.set_state(EditPrice.value)
        await state.update_data(product_id=pid)
        await callback.message.answer(f"«{product.name}» uchun yangi narx (so'm):", reply_markup=kb.cancel_menu())
        await callback.answer()
    elif action == "stock":
        await state.set_state(EditStock.value)
        await state.update_data(product_id=pid)
        await callback.message.answer(f"«{product.name}» uchun yangi qoldiq (soni):", reply_markup=kb.cancel_menu())
        await callback.answer()
    elif action == "toggle":
        product.is_active = not product.is_active
        await session.commit()
        await callback.answer("Holat o'zgardi: " + ("🟢 Faol" if product.is_active else "🔴 Nofaol"), show_alert=True)
    elif action == "delete":
        await catalog_service.soft_delete_product(session, pid)
        await callback.answer("🗑 O'chirildi", show_alert=True)
        try:
            await callback.message.edit_text(f"🗑 <s>{product.name}</s> — o'chirildi")
        except Exception:
            pass


@router.message(EditPrice.value, F.text)
async def edit_price_value(message: Message, state: FSMContext, session: AsyncSession):
    digits = "".join(ch for ch in message.text if ch.isdigit())
    if not digits:
        await message.answer("❗️ Faqat raqam kiriting:")
        return
    data = await state.get_data()
    product = await catalog_service.get_product(session, data["product_id"])
    if product:
        product.price = int(digits)
        await session.commit()
    await state.clear()
    currency = await _currency()
    await message.answer(f"✅ Narx yangilandi: {fmt_money(int(digits), currency)}", reply_markup=kb.main_menu())


@router.message(EditStock.value, F.text)
async def edit_stock_value(message: Message, state: FSMContext, session: AsyncSession):
    digits = "".join(ch for ch in message.text if ch.isdigit())
    if not digits:
        await message.answer("❗️ Faqat raqam kiriting:")
        return
    data = await state.get_data()
    product = await catalog_service.get_product(session, data["product_id"])
    if product:
        product.stock = int(digits)
        await session.commit()
    await state.clear()
    await message.answer(f"✅ Qoldiq yangilandi: {digits} dona", reply_markup=kb.main_menu())


# ─────────────────────────────────────────────────────────────
#  Kategoriyalar
# ─────────────────────────────────────────────────────────────
@router.message(F.text == kb.BTN_ADD_CATEGORY)
async def add_category_start(message: Message, state: FSMContext):
    await state.set_state(AddCategory.name)
    await message.answer("Kategoriya nomini kiriting:", reply_markup=kb.cancel_menu())


@router.message(AddCategory.name, F.text)
async def add_category_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddCategory.emoji)
    await message.answer("Emoji yuboring (yoki o'tkazib yuboring):", reply_markup=_skip_kb())


@router.message(AddCategory.emoji, F.text)
async def add_category_emoji(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    emoji = "🛍" if message.text == BTN_SKIP else message.text.strip()[:8]
    cat = await catalog_service.create_category(session, name=data["name"], emoji=emoji)
    await state.clear()
    await message.answer(f"✅ Kategoriya qo'shildi: {cat.emoji} {cat.name}", reply_markup=kb.main_menu())


@router.message(F.text == kb.BTN_CATEGORIES)
async def list_categories(message: Message, session: AsyncSession):
    cats = await catalog_service.list_categories(session, only_active=False)
    if not cats:
        await message.answer("Kategoriyalar yo'q.")
        return
    lines = [f"{c.emoji} {c.name} {'🟢' if c.is_active else '🔴'}" for c in cats]
    await message.answer("🗂 <b>Kategoriyalar:</b>\n\n" + "\n".join(lines))


# ─────────────────────────────────────────────────────────────
#  Statistika
# ─────────────────────────────────────────────────────────────
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

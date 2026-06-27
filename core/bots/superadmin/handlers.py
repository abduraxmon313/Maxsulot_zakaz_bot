"""Super Admin bot handlerlari: do'kon sozlamalari, analitika, holat."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import BaseFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import WEBAPP_URL, is_superadmin
from core.models.user import User
from core.services import catalog_service, order_service, settings_service
from core.services.i18n import STATUS_LABELS
from core.utils import fmt_money
from core.bots.superadmin import keyboards as kb
from core.bots.superadmin.states import EditSetting

logger = logging.getLogger(__name__)
router = Router()


class IsSuperAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        user = getattr(event, "from_user", None)
        return bool(user and is_superadmin(user.id))


router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    shop = await settings_service.get("shop_name", "Do'kon")
    await message.answer(
        f"👑 <b>Super Admin panel</b>\n🏪 {shop}\n\n"
        "Bu yerdan do'koningizni har qanday biznesga moslang: nom, salom xabari, "
        "rasm, valyuta, narxlar va h.k.",
        reply_markup=kb.main_menu(),
    )


@router.message(F.text == kb.BTN_CANCEL)
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=kb.main_menu())


# ─────────────────────────────────────────────────────────────
#  Sozlamalar
# ─────────────────────────────────────────────────────────────
@router.message(F.text == kb.BTN_SETTINGS)
async def show_settings(message: Message):
    lines = ["⚙️ <b>Do'kon sozlamalari</b>\n", "O'zgartirish uchun tugmani bosing:\n"]
    for key, label, _typ in kb.EDITABLE_SETTINGS:
        val = await settings_service.get(key, "")
        if key == "welcome_image":
            val = "✅ o'rnatilgan" if val else "—"
        elif len(val) > 40:
            val = val[:40] + "…"
        lines.append(f"• {label}: <code>{val or '—'}</code>")
    await message.answer("\n".join(lines), reply_markup=kb.settings_inline())


@router.callback_query(F.data.startswith("set:"))
async def choose_setting(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":", 1)[1]
    typ = kb.SETTING_TYPES.get(key, "text")
    label = kb.SETTING_LABELS.get(key, key)
    current = await settings_service.get(key, "")
    await state.set_state(EditSetting.value)
    await state.update_data(key=key, typ=typ)

    if typ == "image":
        prompt = "🖼 Yangi rasmni yuboring (yoki «o'chirish» deb yozing):"
    elif typ == "int":
        prompt = "Yangi qiymatni raqamda kiriting (so'm):"
    else:
        prompt = "Yangi qiymatni kiriting:"

    shown = ("✅ o'rnatilgan" if (key == "welcome_image" and current) else (current or "—"))
    await callback.message.answer(
        f"<b>{label}</b>\nJoriy qiymat: <code>{shown}</code>\n\n{prompt}",
        reply_markup=kb.cancel_menu(),
    )
    await callback.answer()


@router.message(EditSetting.value, F.photo)
async def save_setting_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("key")
    if data.get("typ") != "image":
        await message.answer("Bu sozlama uchun rasm emas, matn kiriting.")
        return
    await settings_service.set(key, message.photo[-1].file_id)
    await state.clear()
    await message.answer("✅ Rasm saqlandi.", reply_markup=kb.main_menu())


@router.message(EditSetting.value, F.text)
async def save_setting_text(message: Message, state: FSMContext):
    data = await state.get_data()
    key = data.get("key")
    typ = data.get("typ", "text")
    value = message.text.strip()

    if typ == "image":
        if value.lower() in ("o'chirish", "ochirish", "delete", "-"):
            await settings_service.set(key, "")
            await state.clear()
            await message.answer("✅ Rasm o'chirildi.", reply_markup=kb.main_menu())
        else:
            await message.answer("🖼 Iltimos, rasm yuboring yoki «o'chirish» deb yozing.")
        return

    if typ == "int":
        digits = "".join(ch for ch in value if ch.isdigit())
        if not digits:
            await message.answer("❗️ Faqat raqam kiriting:")
            return
        value = digits

    await settings_service.set(key, value)
    await state.clear()
    label = kb.SETTING_LABELS.get(key, key)
    await message.answer(f"✅ Saqlandi: <b>{label}</b>", reply_markup=kb.main_menu())


# ─────────────────────────────────────────────────────────────
#  Do'kon ochiq/yopiq
# ─────────────────────────────────────────────────────────────
@router.message(F.text == kb.BTN_TOGGLE_OPEN)
async def toggle_open(message: Message):
    is_open = await settings_service.get_bool("is_open", True)
    new = not is_open
    await settings_service.set("is_open", "1" if new else "0")
    state_txt = "🟢 OCHIQ — buyurtmalar qabul qilinmoqda" if new else "🔴 YOPIQ — buyurtmalar to'xtatildi"
    await message.answer(f"Do'kon holati: <b>{state_txt}</b>", reply_markup=kb.main_menu())


# ─────────────────────────────────────────────────────────────
#  Analitika
# ─────────────────────────────────────────────────────────────
@router.message(F.text == kb.BTN_ANALYTICS)
async def analytics(message: Message, session: AsyncSession):
    s = await order_service.stats_summary(session)
    currency = await settings_service.get("currency", "so'm")
    users = int((await session.execute(select(func.count(User.id)))).scalar() or 0)
    products = await catalog_service.count_active_products(session)

    # Status bo'yicha taqsimot
    rows = (await session.execute(
        select(order_service.Order.status, func.count(order_service.Order.id))
        .group_by(order_service.Order.status)
    )).all()
    status_lines = [f"   {STATUS_LABELS.get(st, st)}: {cnt}" for st, cnt in rows]

    text = (
        "📊 <b>Analitika</b>\n\n"
        f"💰 Umumiy tushum: <b>{fmt_money(s['revenue'], currency)}</b>\n"
        f"📦 Jami buyurtmalar: {s['total_orders']}\n"
        f"📅 Bugun: {s['today_orders']}\n"
        f"🆕 Kutilmoqda: {s['pending']}\n\n"
        f"👥 Mijozlar: {users}\n"
        f"🛍 Faol mahsulotlar: {products}\n\n"
        "<b>Buyurtmalar holati bo'yicha:</b>\n" + ("\n".join(status_lines) or "   —")
    )
    await message.answer(text)


# ─────────────────────────────────────────────────────────────
#  Tizim holati
# ─────────────────────────────────────────────────────────────
@router.message(F.text == kb.BTN_STATUS)
async def system_status(message: Message):
    from core.bots import registry

    webapp = WEBAPP_URL or "❗️ o'rnatilmagan (WEBAPP_URL)"
    is_open = await settings_service.get_bool("is_open", True)
    await message.answer(
        "ℹ️ <b>Tizim holati</b>\n\n"
        f"🛒 Sotuv bot: {'🟢' if registry.customer_bot else '🔴'}\n"
        f"👨‍💼 Admin bot: {'🟢' if registry.admin_bot else '🔴'}\n"
        f"👑 Super Admin bot: {'🟢' if registry.superadmin_bot else '🔴'}\n"
        f"🌐 Mini App: <code>{webapp}</code>\n"
        f"🏪 Do'kon: {'🟢 ochiq' if is_open else '🔴 yopiq'}"
    )

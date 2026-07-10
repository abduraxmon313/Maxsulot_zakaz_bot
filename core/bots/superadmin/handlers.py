"""
Super Admin bot handlerlari.

Super Admin: do'konni har biznesga moslaydi (nom, salom xabari/rasmi, valyuta,
narxlar), KATEGORIYA va MAHSULOT qo'shadi/tahrirlaydi, analitikani ko'radi.

MUHIM (rasm bug fix): yuklangan rasmlar darhol yuklab olinib, baytlari DB'ga
(Media) saqlanadi — shuning uchun Mini App va Sotuv bot uni muammosiz ko'rsatadi.
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import BaseFilter, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import WEBAPP_URL
from core.models.user import User
from core.services import admin_service, catalog_service, media_service, order_service, settings_service
from core.services.i18n import STATUS_LABELS
from core.utils import fmt_money
from core.bots.superadmin import keyboards as kb
from core.bots.superadmin.states import (
    AddAdminRole, AddCategory, AddProduct, EditPrice, EditSetting, EditStock, ShopLocation,
)

logger = logging.getLogger(__name__)
router = Router()


class IsSuperAdmin(BaseFilter):
    async def __call__(self, event) -> bool:
        user = getattr(event, "from_user", None)
        if not user:
            return False
        # Env doim tekshiriladi (root doim ochiq). DB rollarini keshdan olamiz —
        # ensure_loaded TTL bilan yangilaydi (yangi qo'shilgan superadmin darhol ta'sir qiladi).
        await admin_service.ensure_loaded()
        return admin_service.is_superadmin_sync(user.id)


router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())


async def _currency() -> str:
    return await settings_service.get("currency", "so'm")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    shop = await settings_service.get("shop_name", "Do'kon")
    await message.answer(
        f"👑 <b>Super Admin panel</b>\n🏪 {shop}\n\n"
        "Do'koningizni istalgan biznesga moslang: nom, salom xabari, rasm, valyuta, "
        "narxlar. Kategoriya va mahsulotlarni shu yerdan qo'shasiz.",
        reply_markup=kb.main_menu(),
    )


# Bekor qilish — har qanday FSM holatdan chiqaradi (eng yuqori ustuvorlik).
@router.message(F.text == kb.BTN_CANCEL)
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=kb.main_menu())


# ═════════════════════════════════════════════════════════════
#  SOZLAMALAR
# ═════════════════════════════════════════════════════════════
@router.message(F.text == kb.BTN_SETTINGS)
async def show_settings(message: Message):
    lines = ["⚙️ <b>Do'kon sozlamalari</b>\n", "O'zgartirish uchun tugmani bosing:\n"]
    for key, label, _typ in kb.EDITABLE_SETTINGS:
        val = await settings_service.get(key, "")
        if _typ == "image":
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
    elif key == "working_hours":
        prompt = (
            "Ish vaqtini <b>24 soatlik</b> formatda kiriting.\n"
            "Namuna: <code>09:00 - 22:00</code>\n\n"
            "• Tungi ish uchun: <code>22:00 - 06:00</code>\n"
            "• 24 soat ochiq uchun: <code>00:00 - 24:00</code>\n"
            "Vaqt O'zbekiston vaqti (Toshkent) bo'yicha hisoblanadi."
        )
    else:
        prompt = "Yangi qiymatni kiriting:"

    shown = ("✅ o'rnatilgan" if (typ == "image" and current) else (current or "—"))
    await callback.message.answer(
        f"<b>{label}</b>\nJoriy qiymat: <code>{shown}</code>\n\n{prompt}",
        reply_markup=kb.cancel_menu(),
    )
    await callback.answer()


@router.message(EditSetting.value, F.photo)
async def save_setting_photo(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    key = data.get("key")
    if data.get("typ") != "image":
        await message.answer("Bu sozlama uchun rasm emas, matn kiriting.")
        return
    # Rasmni DB'ga (Media) saqlaymiz — keyin Sotuv bot ham ko'rsata oladi.
    media = await media_service.save_from_telegram(session, message.bot, message.photo[-1].file_id)
    if not media:
        await message.answer("❗️ Rasmni saqlab bo'lmadi, qayta urinib ko'ring.")
        return
    await settings_service.set(key, str(media.id))
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


# ═════════════════════════════════════════════════════════════
#  KATEGORIYA
# ═════════════════════════════════════════════════════════════
@router.message(F.text == kb.BTN_ADD_CATEGORY)
async def add_category_start(message: Message, state: FSMContext):
    await state.set_state(AddCategory.name)
    await message.answer("Kategoriya nomini kiriting:", reply_markup=kb.cancel_menu())


@router.message(AddCategory.name, F.text)
async def add_category_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(AddCategory.emoji)
    await message.answer("Emoji yuboring (yoki o'tkazib yuboring):", reply_markup=kb.skip_menu())


@router.message(AddCategory.emoji, F.text)
async def add_category_emoji(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    emoji = "🛍" if message.text == kb.BTN_SKIP else message.text.strip()[:8]
    cat = await catalog_service.create_category(session, name=data["name"], emoji=emoji)
    await state.clear()
    await message.answer(f"✅ Kategoriya qo'shildi: {cat.emoji} {cat.name}", reply_markup=kb.main_menu())


@router.message(F.text == kb.BTN_CATEGORIES)
async def list_categories(message: Message, session: AsyncSession):
    cats = await catalog_service.list_categories(session, only_active=False)
    if not cats:
        await message.answer("Kategoriyalar yo'q. ➕ Kategoriya tugmasi orqali qo'shing.")
        return
    lines = [f"{c.emoji} {c.name} {'🟢' if c.is_active else '🔴'}" for c in cats]
    await message.answer("🗂 <b>Kategoriyalar:</b>\n\n" + "\n".join(lines))


# ═════════════════════════════════════════════════════════════
#  MAHSULOT QO'SHISH (FSM)
# ═════════════════════════════════════════════════════════════
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
        await message.answer("Mahsulot rasmini yuboring (yoki o'tkazib yuboring):", reply_markup=kb.skip_menu())


@router.callback_query(AddProduct.category, F.data.startswith("pcat:"))
async def add_product_category(callback: CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=cat_id or None)
    await state.set_state(AddProduct.photo)
    await callback.message.answer("Mahsulot rasmini yuboring (yoki o'tkazib yuboring):", reply_markup=kb.skip_menu())
    await callback.answer()


@router.message(AddProduct.photo, F.photo)
async def add_product_photo(message: Message, state: FSMContext, session: AsyncSession):
    # Rasmni DB'ga (Media) saqlaymiz — Mini App'da ko'rinadi.
    media = await media_service.save_from_telegram(session, message.bot, message.photo[-1].file_id)
    await _finish_product(message, state, session, image_media_id=(media.id if media else None))


@router.message(AddProduct.photo, F.text)
async def add_product_photo_skip(message: Message, state: FSMContext, session: AsyncSession):
    await _finish_product(message, state, session, image_media_id=None)


async def _finish_product(message, state, session, image_media_id):
    data = await state.get_data()
    product = await catalog_service.create_product(
        session,
        name=data["name"],
        price=data["price"],
        category_id=data.get("category_id"),
        stock=data.get("stock", 0),
        image_media_id=image_media_id,
    )
    await state.clear()
    currency = await _currency()
    img_note = "🖼 rasm bilan" if image_media_id else "🚫 rasmsiz"
    await message.answer(
        f"✅ Mahsulot qo'shildi ({img_note}):\n<b>{product.name}</b> — "
        f"{fmt_money(product.price, currency)}\nQoldiq: {product.stock}",
        reply_markup=kb.main_menu(),
    )


# ═════════════════════════════════════════════════════════════
#  MAHSULOTLAR RO'YXATI VA TAHRIRLASH
# ═════════════════════════════════════════════════════════════
@router.message(F.text == kb.BTN_PRODUCTS)
async def list_products(message: Message, session: AsyncSession):
    products = await catalog_service.list_products(session, only_active=False, limit=40)
    if not products:
        await message.answer("Mahsulotlar yo'q. ➕ Mahsulot tugmasi orqali qo'shing.")
        return
    currency = await _currency()
    for p in products:
        flag = "🟢" if (p.is_active and p.deleted_at is None) else "🔴"
        img = "🖼" if p.image_media_id else "🚫"
        await message.answer(
            f"{flag} <b>{p.name}</b>\n💰 {fmt_money(p.price, currency)} | 📦 {p.stock} dona | {img}",
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
        await callback.answer("🟢 Faol" if product.is_active else "🔴 Nofaol", show_alert=True)
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


# ═════════════════════════════════════════════════════════════
#  DO'KON OCHIQ/YOPIQ
# ═════════════════════════════════════════════════════════════
async def _shop_status_text() -> str:
    force_closed = await settings_service.get_bool("force_closed", False)
    hours = await settings_service.get("working_hours", "")
    effective = await settings_service.is_shop_open()
    if effective:
        line = "🟢 <b>OCHIQ</b> — buyurtmalar qabul qilinmoqda"
    elif force_closed:
        line = "🔴 <b>YOPIQ</b> — siz qo'lda vaqtincha yopib qo'ygansiz"
    else:
        line = f"🟡 <b>Hozir ish vaqti emas</b> ({hours}) — ish vaqti kelganda ochiladi"
    return (
        f"🏪 <b>Do'kon holati</b>\n\n{line}\n\n"
        f"🕒 Ish vaqti: <code>{hours or '—'}</code> (O‘zbekiston vaqti)\n"
        "Pastdagi tugma bilan boshqaring."
    )


@router.message(F.text == kb.BTN_TOGGLE_OPEN)
async def shop_status_menu(message: Message):
    # Ko'r-ko'rona toggle o'rniga — joriy holatni ko'rsatamiz va aniq tugma beramiz.
    force_closed = await settings_service.get_bool("force_closed", False)
    await message.answer(await _shop_status_text(), reply_markup=kb.shop_status_inline(force_closed))


@router.callback_query(F.data == "shopopen")
async def shop_open(callback: CallbackQuery):
    await settings_service.set("force_closed", "0")
    try:
        await callback.message.edit_text(await _shop_status_text(), reply_markup=kb.shop_status_inline(False))
    except Exception:
        pass
    await callback.answer("🟢 Do'kon ish vaqti bo'yicha ochiq")


@router.callback_query(F.data == "shopclose")
async def shop_close(callback: CallbackQuery):
    await settings_service.set("force_closed", "1")
    try:
        await callback.message.edit_text(await _shop_status_text(), reply_markup=kb.shop_status_inline(True))
    except Exception:
        pass
    await callback.answer("🔴 Do'kon vaqtincha yopildi")


# ═════════════════════════════════════════════════════════════
#  DO'KON MANZILI (lokatsiya + izoh)
# ═════════════════════════════════════════════════════════════
@router.callback_query(F.data == "shoploc")
async def shop_location_from_settings(callback: CallbackQuery, state: FSMContext):
    # «Do'kon sozlamalari» ichidagi 📍 tugmasi orqali ham lokatsiya qo'yish mumkin.
    await callback.answer()
    await shop_location_start(callback.message, state)


@router.message(F.text == kb.BTN_SHOP_LOCATION)
async def shop_location_start(message: Message, state: FSMContext):
    lat = await settings_service.get("shop_lat", "")
    lng = await settings_service.get("shop_lng", "")
    note = await settings_service.get("shop_address", "")
    current = "Hozircha o'rnatilmagan."
    if lat and lng:
        from core.utils import yandex_maps_link
        current = f"📍 {note or 'manzil'}\n🗺 {yandex_maps_link(float(lat), float(lng))}"
    await state.set_state(ShopLocation.location)
    await message.answer(
        f"📍 <b>Do'kon manzili</b>\n\nJoriy: {current}\n\n"
        "Yangi lokatsiyani yuboring (pastdagi «📍 Lokatsiyani yuborish» tugmasi orqali "
        "yoki 📎 → Location).",
        reply_markup=kb.location_request_menu(),
    )


@router.message(ShopLocation.location, F.location)
async def shop_location_received(message: Message, state: FSMContext):
    await state.update_data(lat=message.location.latitude, lng=message.location.longitude)
    await state.set_state(ShopLocation.comment)
    await message.answer(
        "✍️ Endi manzil izohini yozing (masalan: «Chilonzor 5, oynali bino, 1-qavat»).\n"
        "Yoki izohsiz saqlash uchun «⏭ O'tkazib yuborish».",
        reply_markup=kb.skip_menu(),
    )


@router.message(ShopLocation.location, F.text)
async def shop_location_need(message: Message):
    if message.text == kb.BTN_CANCEL:
        return  # umumiy cancel handleri hal qiladi
    await message.answer("📍 Iltimos, lokatsiyani yuboring (tugma orqali yoki 📎 → Location).")


@router.message(ShopLocation.comment, F.text)
async def shop_location_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    comment = "" if message.text == kb.BTN_SKIP else message.text.strip()[:400]
    await settings_service.set("shop_lat", str(data.get("lat", "")))
    await settings_service.set("shop_lng", str(data.get("lng", "")))
    await settings_service.set("shop_address", comment)
    await state.clear()
    await message.answer(
        "✅ Do'kon manzili saqlandi. Endi mijozlar «📍 Do'kon manzili» tugmasi orqali "
        "ko'ra oladi.",
        reply_markup=kb.main_menu(),
    )


# ═════════════════════════════════════════════════════════════
#  ANALITIKA
# ═════════════════════════════════════════════════════════════
@router.message(F.text == kb.BTN_ANALYTICS)
async def analytics(message: Message, session: AsyncSession):
    s = await order_service.stats_summary(session)
    currency = await settings_service.get("currency", "so'm")
    users = int((await session.execute(select(func.count(User.id)))).scalar() or 0)
    products = await catalog_service.count_active_products(session)

    rows = (await session.execute(
        select(order_service.Order.status, func.count(order_service.Order.id))
        .group_by(order_service.Order.status)
    )).all()
    status_lines = [f"   {STATUS_LABELS.get(st, st)}: {cnt}" for st, cnt in rows]

    await message.answer(
        "📊 <b>Analitika</b>\n\n"
        f"💰 Umumiy tushum: <b>{fmt_money(s['revenue'], currency)}</b>\n"
        f"📦 Jami buyurtmalar: {s['total_orders']}\n"
        f"📅 Bugun: {s['today_orders']}\n"
        f"🆕 Kutilmoqda: {s['pending']}\n\n"
        f"👥 Mijozlar: {users}\n"
        f"🛍 Faol mahsulotlar: {products}\n\n"
        "<b>Buyurtmalar holati bo'yicha:</b>\n" + ("\n".join(status_lines) or "   —")
    )


# ═════════════════════════════════════════════════════════════
#  TIZIM HOLATI
# ═════════════════════════════════════════════════════════════
@router.message(F.text == kb.BTN_STATUS)
async def system_status(message: Message):
    from core.bots import registry

    webapp = WEBAPP_URL or "❗️ o'rnatilmagan (WEBAPP_URL)"
    force_closed = await settings_service.get_bool("force_closed", False)
    hours = await settings_service.get("working_hours", "")
    effective = await settings_service.is_shop_open()
    await message.answer(
        "ℹ️ <b>Tizim holati</b>\n\n"
        f"🛒 Sotuv bot: {'🟢' if registry.customer_bot else '🔴'}\n"
        f"👨‍💼 Admin bot: {'🟢' if registry.admin_bot else '🔴'}\n"
        f"👑 Super Admin bot: {'🟢' if registry.superadmin_bot else '🔴'}\n"
        f"🌐 Mini App: <code>{webapp}</code>\n\n"
        f"🏪 Do'kon holati: <b>{'🟢 OCHIQ' if effective else '🔴 YOPIQ'}</b>\n"
        f"   • Majburiy yopish: {'🔴 YOQILGAN (vaqtincha yopiq)' if force_closed else '🟢 yo‘q'}\n"
        f"   • Ish vaqti: <code>{hours or '—'}</code> (O‘zbekiston vaqti)"
    )



# ═════════════════════════════════════════════════════════════
#  ADMINLAR / SUPER ADMINLAR BOSHQARUVI
#  (rol qo'shish/o'chirish, ro'yxatlar. Env orqali berilganlar o'chirilmaydi.)
# ═════════════════════════════════════════════════════════════
def _role_title(role: str) -> str:
    return "👑 Super Admin" if role == "superadmin" else "🛡 Admin"


def _fmt_role_row(rec) -> str:
    """Ro'yxat elementi uchun bir qatorli ko'rinish."""
    who = rec.full_name or ""
    uname = f" · @{rec.username}" if rec.username else ""
    return f"• <code>{rec.telegram_id}</code>{(' — ' + who) if who else ''}{uname}"


@router.message(F.text == kb.BTN_ROLES)
async def roles_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👥 <b>Adminlar boshqaruvi</b>\n\n"
        "Bu yerdan admin va super adminlarni qo'shish/chiqarish mumkin.\n"
        "• Qo'shish uchun foydalanuvchining <b>Telegram ID</b> raqami kerak "
        "(u avval botga <code>/start</code> bosgan bo'lsa yaxshi).\n"
        "• Chiqarish — ro'yxatdan tanlab bosiladi (ID kerak emas).",
        reply_markup=kb.roles_menu_inline(),
    )


@router.callback_query(F.data == "roles:menu")
async def roles_menu_cb(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text(
            "👥 <b>Adminlar boshqaruvi</b>\n\nAmalni tanlang:",
            reply_markup=kb.roles_menu_inline(),
        )
    except Exception:
        await callback.message.answer(
            "👥 <b>Adminlar boshqaruvi</b>\n\nAmalni tanlang:",
            reply_markup=kb.roles_menu_inline(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("roles:list:"))
async def roles_list(callback: CallbackQuery, session: AsyncSession):
    role = callback.data.split(":", 2)[2]
    if role not in {"admin", "superadmin"}:
        await callback.answer("Noma'lum rol.", show_alert=True)
        return
    rows = await admin_service.list_by_role(session, role)
    title = _role_title(role) + " ro'yxati"

    # ENV rollari — o'chirib bo'lmaydigan (root) ro'yxat
    env_ids = admin_service.env_superadmin_ids() if role == "superadmin" else admin_service.env_admin_ids()
    text_lines = [f"<b>{title}</b>", ""]
    if env_ids:
        text_lines.append("🔒 <i>ENV (o'chirib bo'lmaydi):</i>")
        for tid in sorted(env_ids):
            text_lines.append(f"• <code>{tid}</code>")
        text_lines.append("")

    if rows:
        text_lines.append("📋 <i>Bot orqali qo'shilgan (chiqarish mumkin):</i>")
        for r in rows:
            text_lines.append(_fmt_role_row(r))
    else:
        text_lines.append("📋 <i>Bot orqali qo'shilgan hech kim yo'q.</i>")

    try:
        await callback.message.edit_text(
            "\n".join(text_lines),
            reply_markup=kb.roles_list_inline(rows, role),
        )
    except Exception:
        await callback.message.answer(
            "\n".join(text_lines),
            reply_markup=kb.roles_list_inline(rows, role),
        )
    await callback.answer()


@router.callback_query(F.data.startswith("roles:add:"))
async def roles_add_prompt(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split(":", 2)[2]
    if role not in {"admin", "superadmin"}:
        await callback.answer("Noma'lum rol.", show_alert=True)
        return
    await state.set_state(AddAdminRole.telegram_id)
    await state.update_data(role=role, added_by=callback.from_user.id)
    await callback.message.answer(
        f"➕ Yangi <b>{_role_title(role)}</b> qo'shish\n\n"
        "Foydalanuvchining <b>Telegram ID</b> raqamini yuboring (faqat raqam).\n\n"
        "💡 Foydalanuvchi o'zining ID sini olishi uchun @userinfobot ga yozishi mumkin. "
        "Yaxshisi u avval botlarimizdan biriga <code>/start</code> bossin — shunda ismi ham saqlanadi.",
        reply_markup=kb.cancel_menu(),
    )
    await callback.answer()


@router.message(AddAdminRole.telegram_id, F.text)
async def roles_add_value(message: Message, state: FSMContext, session: AsyncSession):
    text_raw = (message.text or "").strip()
    # BTN_CANCEL — global handler tomonidan qamrab olinadi
    digits = "".join(ch for ch in text_raw if ch.isdigit())
    if not digits or len(digits) < 5:
        await message.answer(
            "❗️ Telegram ID faqat raqamlardan iborat bo'lishi kerak (odatda 8-10 xonali).\n"
            "Iltimos, qaytadan kiriting:"
        )
        return
    tid = int(digits)
    data = await state.get_data()
    role = data.get("role", "admin")
    added_by = int(data.get("added_by") or message.from_user.id)

    # O'ziga o'zini qo'shish — mantiqsiz, lekin xatolik ham emas.
    # ENV superadmin — allaqachon ochiq huquqli.
    if admin_service.is_env_superadmin(tid) and role == "superadmin":
        await state.clear()
        await message.answer(
            f"ℹ️ <code>{tid}</code> allaqachon ENV orqali super admin. "
            "Qo'shimcha yozuv kerak emas.",
            reply_markup=kb.main_menu(),
        )
        return

    # Foydalanuvchi jadvalidan ism/username ni topamiz (bor bo'lsa).
    from core.services import user_service
    existing_user = await user_service.get_by_telegram_id(session, tid)
    if existing_user is None:
        # Foydalanuvchi hali botga /start bosmagan — ogohlantiramiz, lekin qo'shamiz.
        # (Botni birinchi ochganida user_service.upsert avtomatik ismini saqlaydi.)
        note = ("\n\n⚠️ Bu ID hali biror botga <code>/start</code> bosmagan — "
                "ismi keyinroq avtomatik saqlanadi.")
    else:
        note = ""

    rec = await admin_service.add_role(
        session,
        telegram_id=tid,
        role=role,
        added_by=added_by,
        full_name=(existing_user.full_name if existing_user else ""),
        username=(existing_user.username if existing_user else None),
    )
    await state.clear()
    who = rec.full_name or ""
    await message.answer(
        f"✅ Rol berildi: {_role_title(role)}\n"
        f"👤 <code>{tid}</code>" + (f" — {who}" if who else "") + note,
        reply_markup=kb.main_menu(),
    )


@router.callback_query(F.data.startswith("roles:del:"))
async def roles_delete_prompt(callback: CallbackQuery, session: AsyncSession):
    tid = int(callback.data.split(":")[2])
    rec = await admin_service.get_role(session, tid)
    if rec is None:
        await callback.answer("Yozuv topilmadi (allaqachon o'chirilgan).", show_alert=True)
        return
    # Foydalanuvchi o'zini o'zi chiqarib yubormasin.
    if tid == callback.from_user.id:
        await callback.answer(
            "❗️ O'zingizni chiqarib yuborolmaysiz.",
            show_alert=True,
        )
        return
    name = rec.full_name or (f"@{rec.username}" if rec.username else "")
    await callback.message.answer(
        f"❓ <b>{_role_title(rec.role)}</b> huquqidan chiqarasizmi?\n"
        f"👤 <code>{tid}</code>" + (f" — {name}" if name else ""),
        reply_markup=kb.roles_confirm_delete_inline(tid),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("roles:delok:"))
async def roles_delete_do(callback: CallbackQuery, session: AsyncSession):
    tid = int(callback.data.split(":")[2])
    if tid == callback.from_user.id:
        await callback.answer("❗️ O'zingizni chiqarib yuborolmaysiz.", show_alert=True)
        return
    ok = await admin_service.remove_role(session, tid)
    if ok:
        try:
            await callback.message.edit_text(
                f"🗑 <code>{tid}</code> ro'yxatdan chiqarildi.",
                reply_markup=kb.roles_menu_inline(),
            )
        except Exception:
            await callback.message.answer(
                f"🗑 <code>{tid}</code> ro'yxatdan chiqarildi.",
                reply_markup=kb.roles_menu_inline(),
            )
        await callback.answer("✅ Chiqarildi", show_alert=False)
    else:
        await callback.answer("Yozuv topilmadi.", show_alert=True)

"""
Buyurtma servisi: yaratish (atomik ombor rezervatsiyasi), status mashinasi,
narxni server tomonida qayta hisoblash.

Xavfsizlik/ishonchlilik:
  * Narx mijozdan QABUL QILINMAYDI — server DB'dagi joriy narxdan hisoblaydi.
  * Ombor atomik kamaytiriladi: UPDATE ... WHERE stock >= qty. Bir vaqtda bir
    nechta odam oxirgi mahsulotni olsa, faqat bittasi muvaffaqiyat qoziladi.
  * Statuslar qat'iy state machine bilan boshqariladi (noto'g'ri o'tish bloklanadi).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.order import Order, OrderItem, OrderStatusHistory
from core.models.product import Product
from core.services import settings_service


class OrderError(Exception):
    """Buyurtma yaratishda biznes-qoidaga ko'ra xato (mijozga ko'rsatiladi)."""


# Status mashinasi: qaysi statusdan qaysisiga o'tish mumkin.
TRANSITIONS: dict[str, set[str]] = {
    "created": {"confirmed", "rejected", "canceled"},
    "confirmed": {"preparing", "on_way", "canceled"},
    "preparing": {"on_way", "delivered", "canceled"},
    "on_way": {"delivered", "canceled"},
    "delivered": {"completed"},
    "completed": set(),
    "canceled": set(),
    "rejected": set(),
}

# Statuslar — bularda ombor rezervatsiyasi qaytariladi (qoldiq tiklanadi).
RELEASE_STOCK_STATUSES = {"canceled", "rejected"}


def can_transition(from_status: str, to_status: str) -> bool:
    return to_status in TRANSITIONS.get(from_status, set())


async def _next_order_number(session: AsyncSession) -> int:
    current = (await session.execute(select(func.max(Order.order_number)))).scalar()
    return int(current or 1000) + 1


async def create_order(
    session: AsyncSession,
    *,
    telegram_id: int,
    customer_name: str,
    items: list[dict],          # [{"product_id": int, "qty": int}, ...]
    delivery_type: str = "delivery",
    address: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    phone: str | None = None,
    payment_method: str = "cash",
    is_paid: bool = False,
    delivery_time: str | None = None,
    note: str | None = None,
) -> Order:
    if not items:
        raise OrderError("Savat bo'sh.")

    # 0) Do'kon ochiqligini tekshirish (O'zbekiston vaqti bo'yicha ish vaqti + qo'lda toggle).
    if not await settings_service.is_shop_open():
        raise OrderError("Hozir do'kon yopiq. Iltimos, ish vaqtida qayta urinib ko'ring.")

    # 1) Mahsulotlarni yuklab, narxni SERVER tomonida hisoblaymiz.
    #    Mijoz yuborgan narxga ishonmaymiz.
    qty_by_id: dict[int, int] = {}
    for it in items:
        pid = int(it.get("product_id"))
        qty = int(it.get("qty", 0))
        if qty <= 0:
            continue
        qty_by_id[pid] = qty_by_id.get(pid, 0) + qty
    if not qty_by_id:
        raise OrderError("Savat bo'sh.")

    products = (
        await session.execute(select(Product).where(Product.id.in_(list(qty_by_id.keys()))))
    ).scalars().all()
    product_map = {p.id: p for p in products}

    order_items: list[OrderItem] = []
    items_total = 0
    reserved: list[tuple[int, int]] = []  # (product_id, qty) — xato bo'lsa qaytarish uchun

    for pid, qty in qty_by_id.items():
        product = product_map.get(pid)
        if not product or not product.is_active or product.deleted_at is not None:
            raise OrderError("Ba'zi mahsulotlar endi mavjud emas. Savatni yangilang.")

        # Atomik ombor kamaytirish (race-condition himoyasi).
        result = await session.execute(
            update(Product)
            .where(Product.id == pid, Product.is_active.is_(True), Product.stock >= qty)
            .values(stock=Product.stock - qty)
            .returning(Product.id)
        )
        if result.first() is None:
            # Yetarli emas — shu paytgacha rezerv qilinganlarni qaytaramiz.
            await _release(session, reserved)
            raise OrderError(f"«{product.name}» yetarli emas yoki tugadi.")
        reserved.append((pid, qty))

        line_total = product.price * qty
        items_total += line_total
        order_items.append(OrderItem(
            product_id=pid,
            name_snapshot=product.name,
            price_snapshot=product.price,
            qty=qty,
            line_total=line_total,
        ))

    # 2) Minimal buyurtma summasi.
    min_order = await settings_service.get_int("min_order_amount", 0)
    if min_order > 0 and items_total < min_order:
        await _release(session, reserved)
        raise OrderError(f"Minimal buyurtma summasi: {min_order:,} so'm.".replace(",", " "))

    # 3) Yetkazib berish narxi.
    delivery_fee = 0
    if delivery_type == "delivery":
        delivery_fee = await settings_service.get_int("delivery_fee", 0)
        free_from = await settings_service.get_int("free_delivery_from", 0)
        if free_from > 0 and items_total >= free_from:
            delivery_fee = 0

    grand_total = items_total + delivery_fee

    # 4) Buyurtmani yozamiz.
    order = Order(
        order_number=await _next_order_number(session),
        user_id=telegram_id,
        customer_name=customer_name or "",
        phone=phone,
        delivery_type=delivery_type if delivery_type in ("delivery", "pickup") else "delivery",
        address=address,
        lat=lat,
        lng=lng,
        delivery_time=(delivery_time or None),
        items_total=items_total,
        delivery_fee=delivery_fee,
        discount_total=0,
        grand_total=grand_total,
        payment_method=payment_method if payment_method in ("cash", "card", "online") else "cash",
        is_paid=bool(is_paid),
        paid_at=datetime.utcnow() if is_paid else None,
        status="created",
        note=note,
    )
    order.items = order_items
    session.add(order)
    session.add(OrderStatusHistory(order=order, from_status=None, to_status="created", actor_id=telegram_id))
    await session.commit()
    await session.refresh(order)
    return order


async def _release(session: AsyncSession, reserved: list[tuple[int, int]]):
    """Rezerv qilingan qoldiqni qaytaradi (xato yoki bekor qilishda)."""
    for pid, qty in reserved:
        await session.execute(
            update(Product).where(Product.id == pid).values(stock=Product.stock + qty)
        )
    await session.commit()


async def change_status(
    session: AsyncSession,
    order: Order,
    to_status: str,
    actor_id: int | None = None,
    note: str | None = None,
) -> Order:
    from_status = order.status
    if from_status == to_status:
        return order
    if not can_transition(from_status, to_status):
        raise OrderError(f"«{from_status}» dan «{to_status}» ga o'tib bo'lmaydi.")

    order.status = to_status
    now = datetime.utcnow()
    if to_status == "confirmed":
        order.confirmed_at = now
    elif to_status == "delivered":
        order.delivered_at = now
    elif to_status in ("canceled", "rejected"):
        order.canceled_at = now
        if note:
            order.cancel_reason = note[:255]

    # Bekor/rad — ombor qoldig'ini qaytaramiz.
    if to_status in RELEASE_STOCK_STATUSES:
        for item in order.items:
            if item.product_id:
                await session.execute(
                    update(Product)
                    .where(Product.id == item.product_id)
                    .values(stock=Product.stock + item.qty)
                )

    session.add(OrderStatusHistory(
        order_id=order.id, from_status=from_status, to_status=to_status,
        actor_id=actor_id, note=note,
    ))
    await session.commit()
    await session.refresh(order)
    return order


async def get_order(session: AsyncSession, order_id: int) -> Order | None:
    return await session.get(Order, order_id)


async def mark_paid(session: AsyncSession, order: Order, provider: str) -> Order:
    """Buyurtmani to'langan deb belgilaydi (to'lov provayderi nomi bilan).

    Hozircha haqiqiy to'lov integratsiyasi yo'q — provayder tanlansa buyurtma
    to'langan hisoblanadi. Keyinchalik bu yerda provayder API'si chaqiriladi.
    """
    order.is_paid = True
    order.paid_at = datetime.utcnow()
    # payment_method ustuni String(12) — provayder nomlari (click/uzum/payme/paylov) sig'adi.
    order.payment_method = (provider or "online")[:12]
    await session.commit()
    await session.refresh(order)
    return order


async def list_orders(
    session: AsyncSession,
    telegram_id: int | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Order]:
    stmt = select(Order)
    if telegram_id is not None:
        stmt = stmt.where(Order.user_id == telegram_id)
    if status:
        stmt = stmt.where(Order.status == status)
    stmt = stmt.order_by(Order.created_at.desc()).limit(limit).offset(offset)
    return list((await session.execute(stmt)).scalars().all())


# ── Statistika (Super Admin analiz uchun) ──
async def stats_summary(session: AsyncSession) -> dict:
    total_orders = int((await session.execute(select(func.count(Order.id)))).scalar() or 0)
    revenue = int((await session.execute(
        select(func.coalesce(func.sum(Order.grand_total), 0)).where(
            Order.status.in_(["delivered", "completed"])
        )
    )).scalar() or 0)
    pending = int((await session.execute(
        select(func.count(Order.id)).where(Order.status == "created")
    )).scalar() or 0)
    # Bugungi buyurtmalar
    today = int((await session.execute(
        select(func.count(Order.id)).where(func.date(Order.created_at) == func.current_date())
    )).scalar() or 0)
    return {
        "total_orders": total_orders,
        "revenue": revenue,
        "pending": pending,
        "today_orders": today,
    }

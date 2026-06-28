"""Buyurtma API: yaratish, ro'yxat, batafsil."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.services import order_service, settings_service, user_service
from core.services.order_service import OrderError
from webapp.security import resolve_user
from webapp.serializers import serialize_order

logger = logging.getLogger(__name__)
router = APIRouter()


class OrderItemIn(BaseModel):
    product_id: int
    qty: int = Field(ge=1, le=999)


class CreateOrderIn(BaseModel):
    items: list[OrderItemIn]
    delivery_type: str = "delivery"   # delivery | pickup
    address_id: int | None = None     # saqlangan manzil (afzal)
    address: str | None = None
    lat: float | None = None
    lng: float | None = None
    phone: str | None = None
    payment_method: str = "cash"      # cash | card | online
    note: str | None = None


@router.post("/orders")
async def create_order(payload: CreateOrderIn, request: Request, session: AsyncSession = Depends(get_db)):
    user = resolve_user(request)
    telegram_id = int(user["id"])
    customer_name = " ".join(
        filter(None, [user.get("first_name"), user.get("last_name")])
    ) or (user.get("username") or "Mijoz")

    # Foydalanuvchini yozib qo'yamiz (CRM uchun).
    await user_service.upsert(
        session, telegram_id=telegram_id,
        full_name=customer_name, username=user.get("username"),
    )
    if payload.phone:
        await user_service.set_phone(session, telegram_id, payload.phone.strip()[:32])

    # Manzil: saqlangan manzil (address_id) afzal; bo'lmasa yuborilgan matn/koordinata.
    address_text = (payload.address or "").strip()[:512] or None
    lat, lng = payload.lat, payload.lng
    if payload.address_id:
        from core.services import address_service
        addr = await address_service.get(session, payload.address_id)
        if not addr or addr.user_id != telegram_id:
            raise HTTPException(status_code=400, detail="Manzil topilmadi.")
        address_text = address_service.compose_text(addr)[:512]
        if addr.lat is not None and addr.lng is not None:
            lat, lng = addr.lat, addr.lng

    try:
        order = await order_service.create_order(
            session,
            telegram_id=telegram_id,
            customer_name=customer_name,
            items=[it.model_dump() for it in payload.items],
            delivery_type=payload.delivery_type,
            address=address_text,
            lat=lat,
            lng=lng,
            phone=(payload.phone or "").strip()[:32] or None,
            payment_method=payload.payment_method,
            note=(payload.note or "").strip()[:500] or None,
        )
    except OrderError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Buyurtma yaratishda xato: %s", e)
        raise HTTPException(status_code=500, detail="Buyurtma yaratib bo'lmadi. Qayta urinib ko'ring.")

    currency = await settings_service.get("currency", "so'm")

    # Adminlarga xabar (Telegram API ishlamasa ham buyurtma saqlanib qoladi).
    try:
        from core.bots.admin.notify import notify_new_order
        await notify_new_order(order, currency)
    except Exception as e:
        logger.warning("Admin bildirishnomasi yuborilmadi: %s", e)

    # Mijozga tasdiq xabari.
    try:
        from core.services import notify_service
        await notify_service.notify_customer(
            telegram_id,
            f"🆕 Buyurtmangiz qabul qilindi!\nBuyurtma #{order.order_number}\n"
            f"Jami: {order.grand_total:,} {currency}".replace(",", " "),
        )
    except Exception:
        pass

    return serialize_order(order, currency)


@router.get("/orders")
async def my_orders(request: Request, session: AsyncSession = Depends(get_db)):
    telegram_id = int(resolve_user(request)["id"])
    orders = await order_service.list_orders(session, telegram_id=telegram_id, limit=50)
    currency = await settings_service.get("currency", "so'm")
    return [serialize_order(o, currency) for o in orders]


@router.get("/orders/{order_id}")
async def order_detail(order_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    telegram_id = int(resolve_user(request)["id"])
    order = await order_service.get_order(session, order_id)
    # IDOR himoyasi: faqat o'z buyurtmasini ko'radi.
    if not order or order.user_id != telegram_id:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi.")
    currency = await settings_service.get("currency", "so'm")
    return serialize_order(order, currency)

"""
Buyurtma API — faqat O'QISH (ro'yxat, batafsil).

Buyurtma YARATISH endi Mini App ichida emas, Sotuv bot ichida amalga oshiriladi:
Mini App savatni `Telegram.WebApp.sendData()` orqali botga yuboradi, bot esa
lokatsiya (Telegram native) va to'lovni so'rab, buyurtmani yakunlaydi.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.services import order_service, settings_service
from webapp.security import resolve_user
from webapp.serializers import serialize_order

router = APIRouter()


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

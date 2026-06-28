"""Manzil API: mijozning saqlangan manzillari (uy qo'shish/tanlash)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.services import address_service
from webapp.security import resolve_user
from webapp.serializers import serialize_address

router = APIRouter()


class AddressIn(BaseModel):
    label: str = Field(default="Uy", max_length=40)
    lat: float | None = None
    lng: float | None = None
    street: str | None = Field(default=None, max_length=255)
    house: str | None = Field(default=None, max_length=64)
    apartment: str | None = Field(default=None, max_length=32)
    entrance: str | None = Field(default=None, max_length=32)
    floor: str | None = Field(default=None, max_length=32)
    comment: str | None = Field(default=None, max_length=255)
    make_default: bool = True


@router.get("/addresses")
async def my_addresses(request: Request, session: AsyncSession = Depends(get_db)):
    telegram_id = int(resolve_user(request)["id"])
    rows = await address_service.list_for_user(session, telegram_id)
    return [serialize_address(a) for a in rows]


@router.post("/addresses")
async def add_address(payload: AddressIn, request: Request, session: AsyncSession = Depends(get_db)):
    telegram_id = int(resolve_user(request)["id"])
    addr = await address_service.create(
        session, telegram_id,
        label=payload.label, lat=payload.lat, lng=payload.lng,
        street=payload.street, house=payload.house, apartment=payload.apartment,
        entrance=payload.entrance, floor=payload.floor, comment=payload.comment,
        make_default=payload.make_default,
    )
    return serialize_address(addr)


@router.post("/addresses/{address_id}/default")
async def make_default(address_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    telegram_id = int(resolve_user(request)["id"])
    ok = await address_service.set_default(session, telegram_id, address_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Manzil topilmadi.")
    return {"ok": True}


@router.delete("/addresses/{address_id}")
async def delete_address(address_id: int, request: Request, session: AsyncSession = Depends(get_db)):
    telegram_id = int(resolve_user(request)["id"])
    ok = await address_service.delete(session, telegram_id, address_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Manzil topilmadi.")
    return {"ok": True}

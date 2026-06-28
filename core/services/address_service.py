"""Mijoz manzillari bilan ishlash."""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.address import Address


async def list_for_user(session: AsyncSession, telegram_id: int) -> list[Address]:
    stmt = (
        select(Address)
        .where(Address.user_id == telegram_id)
        .order_by(Address.is_default.desc(), Address.id.desc())
    )
    return list((await session.execute(stmt)).scalars().all())


async def get(session: AsyncSession, address_id: int) -> Address | None:
    return await session.get(Address, address_id)


async def get_default(session: AsyncSession, telegram_id: int) -> Address | None:
    rows = await list_for_user(session, telegram_id)
    return rows[0] if rows else None


async def _clear_defaults(session: AsyncSession, telegram_id: int):
    await session.execute(
        update(Address).where(Address.user_id == telegram_id).values(is_default=False)
    )


async def create(session: AsyncSession, telegram_id: int, *, label: str = "Uy",
                 lat: float | None = None, lng: float | None = None,
                 street: str | None = None, house: str | None = None,
                 apartment: str | None = None, entrance: str | None = None,
                 floor: str | None = None, comment: str | None = None,
                 make_default: bool = True) -> Address:
    existing = await list_for_user(session, telegram_id)
    is_default = make_default or not existing
    if is_default:
        await _clear_defaults(session, telegram_id)
    addr = Address(
        user_id=telegram_id, label=(label or "Uy")[:40], lat=lat, lng=lng,
        street=(street or None), house=(house or None), apartment=(apartment or None),
        entrance=(entrance or None), floor=(floor or None), comment=(comment or None),
        is_default=is_default,
    )
    session.add(addr)
    await session.commit()
    await session.refresh(addr)
    return addr


async def set_default(session: AsyncSession, telegram_id: int, address_id: int) -> bool:
    addr = await session.get(Address, address_id)
    if not addr or addr.user_id != telegram_id:
        return False
    await _clear_defaults(session, telegram_id)
    addr.is_default = True
    await session.commit()
    return True


async def delete(session: AsyncSession, telegram_id: int, address_id: int) -> bool:
    addr = await session.get(Address, address_id)
    if not addr or addr.user_id != telegram_id:
        return False
    was_default = addr.is_default
    await session.delete(addr)
    await session.commit()
    # Agar standart manzil o'chsa, qolganlardan birini standart qilamiz.
    if was_default:
        rest = await list_for_user(session, telegram_id)
        if rest:
            rest[0].is_default = True
            await session.commit()
    return True


def compose_text(addr: Address) -> str:
    """Manzilni o'qiladigan matnga aylantiradi (buyurtma/admin uchun)."""
    parts = []
    if addr.street:
        parts.append(addr.street)
    if addr.house:
        parts.append(f"uy {addr.house}")
    if addr.apartment:
        parts.append(f"kv {addr.apartment}")
    if addr.entrance:
        parts.append(f"{addr.entrance}-podyezd")
    if addr.floor:
        parts.append(f"{addr.floor}-etaj")
    text = ", ".join(parts)
    if addr.comment:
        text = f"{text} ({addr.comment})" if text else addr.comment
    return text or (addr.label or "Manzil")

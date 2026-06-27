"""Foydalanuvchi (mijoz) yozuvini yaratish/yangilash."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import DEFAULT_LANGUAGE
from core.models.user import User


async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    return (
        await session.execute(select(User).where(User.telegram_id == telegram_id))
    ).scalar_one_or_none()


async def upsert(
    session: AsyncSession,
    telegram_id: int,
    full_name: str = "",
    username: str | None = None,
    language: str | None = None,
) -> User:
    user = await get_by_telegram_id(session, telegram_id)
    if user is None:
        user = User(
            telegram_id=telegram_id,
            full_name=full_name or "",
            username=username,
            language=language or DEFAULT_LANGUAGE,
        )
        session.add(user)
    else:
        if full_name:
            user.full_name = full_name
        if username is not None:
            user.username = username
    await session.commit()
    await session.refresh(user)
    return user


async def set_language(session: AsyncSession, telegram_id: int, language: str) -> None:
    user = await get_by_telegram_id(session, telegram_id)
    if user:
        user.language = language
        await session.commit()


async def set_phone(session: AsyncSession, telegram_id: int, phone: str) -> None:
    user = await get_by_telegram_id(session, telegram_id)
    if user:
        user.phone = phone
        await session.commit()


async def get_language(session: AsyncSession, telegram_id: int) -> str:
    user = await get_by_telegram_id(session, telegram_id)
    return (user.language if user else None) or DEFAULT_LANGUAGE

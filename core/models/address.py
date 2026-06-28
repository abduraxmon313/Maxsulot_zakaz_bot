"""Mijoz manzillari (Uzum Tezkor uslubidagi "uy qo'shish")."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)  # telegram_id
    label: Mapped[str] = mapped_column(String(40), default="Uy")   # Uy | Ish | Boshqa
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    street: Mapped[str | None] = mapped_column(String(255), nullable=True)   # ko'cha / orientir
    house: Mapped[str | None] = mapped_column(String(64), nullable=True)
    apartment: Mapped[str | None] = mapped_column(String(32), nullable=True)
    entrance: Mapped[str | None] = mapped_column(String(32), nullable=True)  # podyezd
    floor: Mapped[str | None] = mapped_column(String(32), nullable=True)     # etaj
    comment: Mapped[str | None] = mapped_column(String(255), nullable=True)  # kuryerga izoh
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

"""Mahsulot kategoriyalari."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    # Standart belgi — organik sut mahsulotlari biznesiga mos (avval "🛍" edi).
    # catalog_service.create_category() ham shu qiymatni ishlatadi.
    emoji: Mapped[str] = mapped_column(String(8), default="🥛")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

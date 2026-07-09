"""
Ma'lumotlar bazasi qatlami (SQLAlchemy 2.0 async + asyncpg).

IntizomAI patterni: jadvallar `create_all` bilan yaratiladi, keyin idempotent
"ADD COLUMN IF NOT EXISTS" migratsiyalari va indekslar qo'shiladi. Bir nechta bot
bitta jarayonda ishlagani uchun jadval yaratish lock + flag bilan FAQAT BIR MARTA
bajariladi.
"""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import DATABASE_URL, DEFAULT_SETTINGS

logger = logging.getLogger(__name__)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_recycle=1800,
    pool_size=10,
    max_overflow=20,
    pool_timeout=30,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency."""
    async with AsyncSessionLocal() as session:
        yield session


_tables_ready = False
_tables_lock = asyncio.Lock()


# ─────────────────────────────────────────────────────────────
#  Idempotent migratsiyalar (eski DB'ga yangi ustun qo'shilsa)
# ─────────────────────────────────────────────────────────────
PRODUCT_NEW_COLUMNS = [
    ("old_price", "INTEGER"),
    ("image_media_id", "INTEGER"),
    ("photo_url", "VARCHAR(512)"),
    ("rating", "DOUBLE PRECISION DEFAULT 0"),
    ("rating_count", "INTEGER DEFAULT 0"),
    ("sort_order", "INTEGER DEFAULT 0"),
    ("is_active", "BOOLEAN DEFAULT TRUE"),
    ("deleted_at", "TIMESTAMP"),
]

ORDER_NEW_COLUMNS = [
    ("lat", "DOUBLE PRECISION"),
    ("lng", "DOUBLE PRECISION"),
    ("discount_total", "INTEGER DEFAULT 0"),
    ("cancel_reason", "VARCHAR(255)"),
    ("is_paid", "BOOLEAN DEFAULT FALSE"),
    ("paid_at", "TIMESTAMP"),
    ("delivery_time", "VARCHAR(32)"),
    ("confirmed_at", "TIMESTAMP"),
    ("delivered_at", "TIMESTAMP"),
    ("canceled_at", "TIMESTAMP"),
]

NEW_INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_products_category ON products (category_id, is_active)",
    "CREATE INDEX IF NOT EXISTS ix_orders_status_created ON orders (status, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_orders_user_created ON orders (user_id, created_at)",
    "CREATE INDEX IF NOT EXISTS ix_order_items_order ON order_items (order_id)",
    "CREATE INDEX IF NOT EXISTS ix_users_telegram ON users (telegram_id)",
]


async def _run_migrations(conn):
    for col, ddl in PRODUCT_NEW_COLUMNS:
        try:
            await conn.execute(text(f'ALTER TABLE products ADD COLUMN IF NOT EXISTS {col} {ddl}'))
        except Exception as e:
            logger.warning(f"Migration skip products.{col}: {e}")
    for col, ddl in ORDER_NEW_COLUMNS:
        try:
            await conn.execute(text(f'ALTER TABLE orders ADD COLUMN IF NOT EXISTS {col} {ddl}'))
        except Exception as e:
            logger.warning(f"Migration skip orders.{col}: {e}")
    for ddl in NEW_INDEXES:
        try:
            await conn.execute(text(ddl))
        except Exception as e:
            logger.warning(f"Index skip: {e}")


async def _seed_settings(session: AsyncSession):
    """Standart sozlamalarni faqat mavjud bo'lmaganda qo'shadi (idempotent)."""
    from core.models.setting import Setting

    for key, value in DEFAULT_SETTINGS.items():
        existing = await session.get(Setting, key)
        if existing is None:
            session.add(Setting(key=key, value=str(value)))
    await session.commit()


async def create_tables():
    global _tables_ready
    async with _tables_lock:
        if _tables_ready:
            return
        # Barcha modellarni import qilamiz — Base.metadata to'lishi uchun.
        from core.models import (  # noqa: F401
            setting, user, category, product, banner, order, media,
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _run_migrations(conn)
        async with AsyncSessionLocal() as session:
            await _seed_settings(session)
        _tables_ready = True
        logger.info("✅ Ma'lumotlar bazasi tayyor (jadvallar + sozlamalar)")

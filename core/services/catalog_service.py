"""Kategoriya va mahsulotlar bilan ishlash."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.category import Category
from core.models.product import Product


# ── Kategoriyalar ──
async def list_categories(session: AsyncSession, only_active: bool = True) -> list[Category]:
    stmt = select(Category)
    if only_active:
        stmt = stmt.where(Category.is_active.is_(True))
    stmt = stmt.order_by(Category.sort_order, Category.id)
    return list((await session.execute(stmt)).scalars().all())


async def create_category(session: AsyncSession, name: str, emoji: str = "🛍") -> Category:
    cat = Category(name=name.strip(), emoji=(emoji or "🛍").strip()[:8])
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat


async def get_category(session: AsyncSession, category_id: int) -> Category | None:
    return await session.get(Category, category_id)


async def delete_category(session: AsyncSession, category_id: int) -> None:
    cat = await session.get(Category, category_id)
    if cat:
        cat.is_active = False
        await session.commit()


# ── Mahsulotlar ──
def _active_filter(stmt):
    return stmt.where(Product.is_active.is_(True), Product.deleted_at.is_(None))


async def list_products(
    session: AsyncSession,
    category_id: int | None = None,
    query: str | None = None,
    only_active: bool = True,
    include_deleted: bool = False,
    sort: str = "popular",
    limit: int = 100,
    offset: int = 0,
) -> list[Product]:
    stmt = select(Product)
    if only_active:
        stmt = _active_filter(stmt)
    elif not include_deleted:
        # only_active=False bilan chaqirilganda ham SOFT-DELETED mahsulotlar
        # standart holatda ko'rinmasin — faqat "aktiv/nofaol" farqi qoladi.
        # (superadmin ro'yxatida o'chirilgan mahsulot ko'rinib qolmasligi uchun)
        stmt = stmt.where(Product.deleted_at.is_(None))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.description.ilike(like)))

    if sort == "cheap":
        stmt = stmt.order_by(Product.price.asc())
    elif sort == "expensive":
        stmt = stmt.order_by(Product.price.desc())
    elif sort == "new":
        stmt = stmt.order_by(Product.created_at.desc())
    else:  # popular
        stmt = stmt.order_by(Product.sort_order, Product.rating.desc(), Product.id.desc())

    stmt = stmt.limit(limit).offset(offset)
    return list((await session.execute(stmt)).scalars().all())


async def get_product(session: AsyncSession, product_id: int) -> Product | None:
    return await session.get(Product, product_id)


async def create_product(
    session: AsyncSession,
    name: str,
    price: int,
    category_id: int | None = None,
    description: str = "",
    stock: int = 0,
    image_file_id: str | None = None,
    image_media_id: int | None = None,
    old_price: int | None = None,
) -> Product:
    product = Product(
        name=name.strip(),
        price=int(price),
        category_id=category_id,
        description=(description or "").strip(),
        stock=int(stock),
        image_file_id=image_file_id,
        image_media_id=image_media_id,
        old_price=old_price,
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


async def soft_delete_product(session: AsyncSession, product_id: int) -> bool:
    from datetime import datetime

    product = await session.get(Product, product_id)
    if not product:
        return False
    product.is_active = False
    product.deleted_at = datetime.utcnow()
    await session.commit()
    return True


async def count_active_products(session: AsyncSession) -> int:
    stmt = _active_filter(select(func.count(Product.id)))
    return int((await session.execute(stmt)).scalar() or 0)

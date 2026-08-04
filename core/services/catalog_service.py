"""Kategoriya va mahsulotlar bilan ishlash."""
from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.banner import Banner
from core.models.category import Category
from core.models.product import Product


# ── Kategoriyalar ──
async def list_categories(session: AsyncSession, only_active: bool = True) -> list[Category]:
    stmt = select(Category)
    if only_active:
        stmt = stmt.where(Category.is_active.is_(True))
    stmt = stmt.order_by(Category.sort_order, Category.id)
    return list((await session.execute(stmt)).scalars().all())


async def create_category(session: AsyncSession, name: str, emoji: str = "🥛") -> Category:
    # Yangi kategoriya ro'yxat oxiriga tushsin — mavjud tartibni buzmaymiz.
    max_order = int(
        (await session.execute(select(func.coalesce(func.max(Category.sort_order), 0)))).scalar() or 0
    )
    cat = Category(
        name=name.strip(),
        emoji=(emoji or "🥛").strip()[:8],
        sort_order=max_order + 1,
    )
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat


async def get_category(session: AsyncSession, category_id: int) -> Category | None:
    return await session.get(Category, category_id)


async def count_categories(session: AsyncSession, only_active: bool = False) -> int:
    stmt = select(func.count(Category.id))
    if only_active:
        stmt = stmt.where(Category.is_active.is_(True))
    return int((await session.execute(stmt)).scalar() or 0)


async def update_category(
    session: AsyncSession,
    category_id: int,
    *,
    name: str | None = None,
    emoji: str | None = None,
    is_active: bool | None = None,
) -> Category | None:
    """Kategoriyaning berilgan maydonlarini yangilaydi (None = tegilmaydi)."""
    cat = await session.get(Category, category_id)
    if not cat:
        return None
    if name is not None:
        cat.name = name.strip()[:120]
    if emoji is not None:
        cat.emoji = (emoji or "🥛").strip()[:8]
    if is_active is not None:
        cat.is_active = bool(is_active)
    await session.commit()
    await session.refresh(cat)
    return cat


async def move_category(session: AsyncSession, category_id: int, direction: int) -> bool:
    """Kategoriyani ro'yxatda yuqoriga (-1) yoki pastga (+1) suradi.

    Qo'shni element bilan `sort_order` almashtiriladi. Shu tufayli Mini App'dagi
    kategoriya tartibi Super Admin xohlagancha bo'ladi (chegaralarda hech nima
    o'zgarmaydi va False qaytadi).
    """
    cats = await list_categories(session, only_active=False)
    idx = next((i for i, c in enumerate(cats) if c.id == category_id), None)
    if idx is None:
        return False
    target = idx + (1 if direction > 0 else -1)
    if target < 0 or target >= len(cats):
        return False
    a, b = cats[idx], cats[target]
    # Tartib qiymatlari teng bo'lishi mumkin (eski yozuvlar) — indeks bilan qayta
    # raqamlab, keyin almashtiramiz. Aks holda swap ta'sir qilmaydi.
    for i, c in enumerate(cats):
        c.sort_order = i
    a.sort_order, b.sort_order = b.sort_order, a.sort_order
    await session.commit()
    return True


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


async def count_products(
    session: AsyncSession,
    category_id: int | None = None,
    query: str | None = None,
    only_active: bool = True,
    include_deleted: bool = False,
) -> int:
    """`list_products` bilan BIR XIL filtrlar bo'yicha son — sahifalash uchun."""
    stmt = select(func.count(Product.id))
    if only_active:
        stmt = _active_filter(stmt)
    elif not include_deleted:
        stmt = stmt.where(Product.deleted_at.is_(None))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if query:
        like = f"%{query.strip()}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.description.ilike(like)))
    return int((await session.execute(stmt)).scalar() or 0)


# Super Admin bot orqali tahrirlanadigan maydonlar (oq ro'yxat — xavfsizlik).
EDITABLE_PRODUCT_FIELDS = {
    "name", "description", "price", "old_price", "stock",
    "category_id", "image_media_id", "sort_order", "is_active",
}


async def update_product(session: AsyncSession, product_id: int, **fields) -> Product | None:
    """Mahsulotning ruxsat etilgan maydonlarini yangilaydi.

    Faqat `EDITABLE_PRODUCT_FIELDS` ichidagi kalitlar qo'llanadi — noma'lum
    maydonlar jimgina tashlab yuboriladi (callback'dan kelgan ma'lumot uchun himoya).
    """
    product = await session.get(Product, product_id)
    if not product:
        return None
    for key, value in fields.items():
        if key in EDITABLE_PRODUCT_FIELDS:
            setattr(product, key, value)
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


async def count_out_of_stock(session: AsyncSession) -> int:
    """Faol, lekin qoldig'i tugagan mahsulotlar soni (analitika ogohlantirishi)."""
    stmt = _active_filter(select(func.count(Product.id))).where(Product.stock <= 0)
    return int((await session.execute(stmt)).scalar() or 0)


# ── Bannerlar (bosh ekrandagi reklama bloklari) ──
async def list_banners(session: AsyncSession, only_active: bool = False) -> list[Banner]:
    stmt = select(Banner)
    if only_active:
        stmt = stmt.where(Banner.is_active.is_(True))
    stmt = stmt.order_by(Banner.sort_order, Banner.id)
    return list((await session.execute(stmt)).scalars().all())


async def get_banner(session: AsyncSession, banner_id: int) -> Banner | None:
    return await session.get(Banner, banner_id)


async def create_banner(
    session: AsyncSession,
    *,
    image_media_id: int | None = None,
    photo_url: str | None = None,
    link_type: str = "none",
    link_value: str | None = None,
) -> Banner:
    max_order = int(
        (await session.execute(select(func.coalesce(func.max(Banner.sort_order), 0)))).scalar() or 0
    )
    banner = Banner(
        image_media_id=image_media_id,
        photo_url=photo_url,
        link_type=link_type if link_type in ("none", "product", "category", "url") else "none",
        link_value=link_value,
        sort_order=max_order + 1,
        is_active=True,
    )
    session.add(banner)
    await session.commit()
    await session.refresh(banner)
    return banner


async def toggle_banner(session: AsyncSession, banner_id: int) -> Banner | None:
    banner = await session.get(Banner, banner_id)
    if not banner:
        return None
    banner.is_active = not banner.is_active
    await session.commit()
    await session.refresh(banner)
    return banner


async def delete_banner(session: AsyncSession, banner_id: int) -> bool:
    """Bannerni butunlay o'chiradi (soft-delete kerak emas — u shunchaki reklama)."""
    banner = await session.get(Banner, banner_id)
    if not banner:
        return False
    await session.delete(banner)
    await session.commit()
    return True

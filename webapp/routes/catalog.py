"""Katalog API: kategoriyalar, mahsulotlar, bannerlar."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.models.banner import Banner
from core.services import catalog_service
from webapp.serializers import serialize_banner, serialize_category, serialize_product

router = APIRouter()


@router.get("/categories")
async def get_categories(session: AsyncSession = Depends(get_db)):
    cats = await catalog_service.list_categories(session)
    return [serialize_category(c) for c in cats]


@router.get("/products")
async def get_products(
    category_id: int | None = None,
    q: str | None = None,
    sort: str = "popular",
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
):
    products = await catalog_service.list_products(
        session,
        category_id=category_id,
        query=q,
        sort=sort,
        limit=min(limit, 200),
        offset=offset,
    )
    return [serialize_product(p) for p in products]


@router.get("/products/{product_id}")
async def get_product(product_id: int, session: AsyncSession = Depends(get_db)):
    product = await catalog_service.get_product(session, product_id)
    if not product or not product.is_active or product.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi.")
    return serialize_product(product, detail=True)


@router.get("/banners")
async def get_banners(session: AsyncSession = Depends(get_db)):
    banners = (
        await session.execute(
            select(Banner).where(Banner.is_active.is_(True)).order_by(Banner.sort_order, Banner.id)
        )
    ).scalars().all()
    return [serialize_banner(b) for b in banners]

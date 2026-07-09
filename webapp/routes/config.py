"""GET /api/config — Mini App uchun do'kon sozlamalari (ochiq ma'lumot)."""
from __future__ import annotations

from fastapi import APIRouter

from core.config import SUPPORTED_LANGUAGES, YANDEX_MAPS_API_KEY
from core.services import settings_service

router = APIRouter()


@router.get("/config")
async def get_config():
    s = await settings_service.get_all()
    is_open = await settings_service.is_shop_open()  # O'zbekiston vaqti bo'yicha
    return {
        "shop_name": s.get("shop_name", "Do'kon"),
        "currency": s.get("currency", "so'm"),
        "phone": s.get("phone", ""),
        "working_hours": s.get("working_hours", ""),
        "is_open": is_open,
        "min_order_amount": int(s.get("min_order_amount", "0") or 0),
        "delivery_fee": int(s.get("delivery_fee", "0") or 0),
        "free_delivery_from": int(s.get("free_delivery_from", "0") or 0),
        "primary_color": s.get("primary_color", "#8B5E3C"),
        "maps_api_key": YANDEX_MAPS_API_KEY,
        "languages": SUPPORTED_LANGUAGES,
        "welcome": {
            "uz": s.get("welcome_uz", ""),
            "ru": s.get("welcome_ru", ""),
            "en": s.get("welcome_en", ""),
        },
    }

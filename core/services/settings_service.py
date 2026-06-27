"""
Do'kon sozlamalari servisi (key/value + xotira keshi).

Sozlamalar tez-tez o'qiladi (har /start, har Mini App config so'rovi), shuning uchun
ular xotirada keshlanadi. Yozishda kesh yangilanadi. Bitta jarayon bo'lgani uchun
(barcha botlar + webapp bir process) bu xavfsiz.
"""
from __future__ import annotations

from sqlalchemy import select

from core.config import DEFAULT_SETTINGS
from core.database import AsyncSessionLocal
from core.models.setting import Setting

_cache: dict[str, str] = {}
_loaded = False


async def _ensure_loaded():
    global _loaded
    if _loaded:
        return
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(select(Setting))).scalars().all()
    _cache.update({r.key: r.value for r in rows})
    # Default qiymatlar bilan to'ldiramiz (DB'da bo'lmaganlari uchun).
    for k, v in DEFAULT_SETTINGS.items():
        _cache.setdefault(k, str(v))
    _loaded = True


async def get_all() -> dict[str, str]:
    await _ensure_loaded()
    return dict(_cache)


async def get(key: str, default: str | None = None) -> str:
    await _ensure_loaded()
    if key in _cache:
        return _cache[key]
    return default if default is not None else str(DEFAULT_SETTINGS.get(key, ""))


async def get_int(key: str, default: int = 0) -> int:
    val = await get(key, str(default))
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return default


async def get_bool(key: str, default: bool = False) -> bool:
    val = await get(key, "1" if default else "0")
    return str(val).strip().lower() in ("1", "true", "yes", "on")


async def set(key: str, value: str) -> None:
    await _ensure_loaded()
    value = "" if value is None else str(value)
    async with AsyncSessionLocal() as session:
        existing = await session.get(Setting, key)
        if existing is None:
            session.add(Setting(key=key, value=value))
        else:
            existing.value = value
        await session.commit()
    _cache[key] = value


def invalidate():
    """Keshni majburan tozalash (test/admin uchun)."""
    global _loaded
    _loaded = False
    _cache.clear()

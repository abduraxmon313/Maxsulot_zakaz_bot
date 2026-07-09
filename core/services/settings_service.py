"""
Do'kon sozlamalari servisi (key/value + xotira keshi).

Sozlamalar tez-tez o'qiladi (har /start, har Mini App config so'rovi), shuning uchun
ular xotirada keshlanadi. Yozishda kesh yangilanadi. Bitta jarayon bo'lgani uchun
(barcha botlar + webapp bir process) bu xavfsiz.
"""
from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import select

from core.config import DEFAULT_SETTINGS, TIMEZONE
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


# ─────────────────────────────────────────────────────────────
#  Ish vaqti (O'zbekiston vaqti — Asia/Tashkent, UTC+5)
# ─────────────────────────────────────────────────────────────
_TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")


def _within_working_hours(hours_str: str) -> bool:
    """
    `working_hours` (masalan "09:00 - 22:00") ni HOZIRGI O'ZBEKISTON VAQTI bilan
    solishtiradi. Server UTC'da ishlasa ham vaqt Asia/Tashkent (UTC+5) bo'yicha
    hisoblanadi.

    - Bo'sh yoki tanib bo'lmasa → har doim ochiq (do'konni bloklamaymiz).
    - start < end  → oddiy oraliq (09:00–22:00).
    - start > end  → tungi oraliq (22:00–06:00).
    - start == end → 24 soat ochiq.
    """
    if not hours_str:
        return True
    matches = _TIME_RE.findall(hours_str)
    if len(matches) < 2:
        return True
    try:
        sh, sm = int(matches[0][0]), int(matches[0][1])
        eh, em = int(matches[1][0]), int(matches[1][1])
    except (ValueError, IndexError):
        return True
    if not (0 <= sh <= 23 and 0 <= eh <= 23 and 0 <= sm <= 59 and 0 <= em <= 59):
        return True

    now = datetime.now(TIMEZONE)
    cur = now.hour * 60 + now.minute
    start = sh * 60 + sm
    end = eh * 60 + em

    if start == end:
        return True
    if start < end:
        return start <= cur < end
    return cur >= start or cur < end


async def is_shop_open() -> bool:
    """
    Do'kon hozir buyurtma qabul qiladimi?
      • Super Admin qo'lda yopib qo'ygan bo'lsa (is_open=0) → yopiq.
      • Aks holda ish vaqti (O'zbekiston vaqti) bo'yicha aniqlanadi.
    """
    if not await get_bool("is_open", True):
        return False
    hours = await get("working_hours", "")
    return _within_working_hours(hours)

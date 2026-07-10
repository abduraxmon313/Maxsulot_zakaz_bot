"""
Adminlar va Super Adminlar boshqaruvi.

Manbalar:
  1) Env: SUPERADMIN_IDS / ADMIN_IDS — root egasi (deployer) tomonidan beriladi.
     Bularni bot orqali O'CHIRIB BO'LMAYDI (xavfsizlik — root doim qoladi).
  2) DB: admin_roles jadvali — Super Admin bot orqali JONLI qo'shilganlar.
     Bularni bot orqali qo'shish/o'chirish mumkin.

is_admin / is_superadmin tekshiruvlari uchun DB IDlari xotira keshida saqlanadi
(TTL 3s) — har chaqiruvda DB'ga bormaslik uchun, lekin har o'zgarishdan keyin
kesh MAJBURIY yangilanadi. Filter (`IsSuperAdmin`) async — DB tekshiruvi
imkoniyati bor.
"""
from __future__ import annotations

import logging
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import ADMIN_IDS as ENV_ADMIN_IDS, SUPERADMIN_IDS as ENV_SUPERADMIN_IDS
from core.database import AsyncSessionLocal
from core.models.admin_role import AdminRole, ROLE_ADMIN, ROLE_SUPERADMIN, VALID_ROLES

logger = logging.getLogger(__name__)

_admin_ids: set[int] = set()          # 'admin' YOKI 'superadmin' rolli (superset)
_superadmin_ids: set[int] = set()     # faqat 'superadmin' rolli
_loaded_at: float = 0.0
_CACHE_TTL = 3.0


async def _refresh_cache() -> None:
    """DB'dagi barcha rollarni xotira keshiga qayta yuklaydi."""
    global _admin_ids, _superadmin_ids, _loaded_at
    async with AsyncSessionLocal() as session:
        rows = list((await session.execute(select(AdminRole))).scalars().all())
    _admin_ids = {int(r.telegram_id) for r in rows}
    _superadmin_ids = {int(r.telegram_id) for r in rows if r.role == ROLE_SUPERADMIN}
    _loaded_at = time.time()


async def ensure_loaded() -> None:
    """Kesh TTL o'tgan bo'lsa yangilaydi. Xavfsizlik uchun xatoda ham qaytadi."""
    if time.time() - _loaded_at <= _CACHE_TTL:
        return
    try:
        await _refresh_cache()
    except Exception as e:
        logger.warning("admin roles kesh yangilashda xato: %s", e)


def cached_admin_ids() -> set[int]:
    return set(_admin_ids)


def cached_superadmin_ids() -> set[int]:
    return set(_superadmin_ids)


def env_admin_ids() -> set[int]:
    return set(ENV_ADMIN_IDS)


def env_superadmin_ids() -> set[int]:
    return set(ENV_SUPERADMIN_IDS)


def all_admin_ids() -> set[int]:
    """ENV + DB — barcha admin (superadminlar ham 'admin' huquqiga ega)."""
    return set(ENV_ADMIN_IDS) | _admin_ids


def all_superadmin_ids() -> set[int]:
    return set(ENV_SUPERADMIN_IDS) | _superadmin_ids


def is_admin_sync(telegram_id: int | None) -> bool:
    """SYNC — kesh + env. Filterlar oldin `await ensure_loaded()` chaqirsin."""
    if telegram_id is None:
        return False
    tid = int(telegram_id)
    return tid in ENV_ADMIN_IDS or tid in _admin_ids


def is_superadmin_sync(telegram_id: int | None) -> bool:
    if telegram_id is None:
        return False
    tid = int(telegram_id)
    return tid in ENV_SUPERADMIN_IDS or tid in _superadmin_ids


def is_env_superadmin(telegram_id: int | None) -> bool:
    """Env orqali berilgan superadmin — DB'dan o'chirilmaydi (root himoyasi)."""
    return telegram_id is not None and int(telegram_id) in ENV_SUPERADMIN_IDS


# ─────────────────────────────────────────────────────────────
#  CRUD
# ─────────────────────────────────────────────────────────────
async def get_role(session: AsyncSession, telegram_id: int) -> AdminRole | None:
    return await session.get(AdminRole, int(telegram_id))


async def list_by_role(session: AsyncSession, role: str) -> list[AdminRole]:
    """Berilgan rol bo'yicha ro'yxat (faqat DB'dagilar)."""
    if role not in VALID_ROLES:
        return []
    stmt = select(AdminRole).where(AdminRole.role == role).order_by(AdminRole.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def list_all(session: AsyncSession) -> list[AdminRole]:
    stmt = select(AdminRole).order_by(AdminRole.created_at.desc())
    return list((await session.execute(stmt)).scalars().all())


async def add_role(
    session: AsyncSession,
    telegram_id: int,
    role: str,
    added_by: int | None = None,
    full_name: str = "",
    username: str | None = None,
) -> AdminRole:
    """Rolni qo'shadi yoki mavjud yozuvni yangilaydi. Keshni majburiy yangilaydi."""
    if role not in VALID_ROLES:
        raise ValueError(f"Noma'lum rol: {role}")
    tid = int(telegram_id)
    existing = await session.get(AdminRole, tid)
    if existing:
        existing.role = role
        if full_name:
            existing.full_name = full_name
        if username is not None:
            existing.username = username
        if added_by:
            existing.added_by = added_by
        rec = existing
    else:
        rec = AdminRole(
            telegram_id=tid,
            role=role,
            full_name=full_name or "",
            username=username,
            added_by=added_by,
        )
        session.add(rec)
    await session.commit()
    await session.refresh(rec)
    await _refresh_cache()
    return rec


async def remove_role(session: AsyncSession, telegram_id: int) -> bool:
    """DB'dan rolni o'chiradi. Env bilan berilganlarga ta'siri yo'q. Keshni yangilaydi."""
    rec = await session.get(AdminRole, int(telegram_id))
    if not rec:
        return False
    await session.delete(rec)
    await session.commit()
    await _refresh_cache()
    return True

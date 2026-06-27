"""
GET /api/image/{file_id} — Telegram'dagi mahsulot rasmini Mini App uchun proxy qiladi.

Mahsulot rasmlari Telegram'da `file_id` sifatida saqlanadi (bepul, tez). Mini App
to'g'ridan-to'g'ri file_id'dan rasm ko'rsata olmaydi, shuning uchun server uni
yuklab beradi va keshlaydi.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from core.bots import registry

logger = logging.getLogger(__name__)
router = APIRouter()

# Oddiy xotira keshi (file_id -> (bytes, content_type)). Hajmi cheklangan.
_cache: dict[str, tuple[bytes, str]] = {}
_MAX_CACHE = 500


def _guess_type(path: str) -> str:
    p = (path or "").lower()
    if p.endswith(".png"):
        return "image/png"
    if p.endswith(".webp"):
        return "image/webp"
    if p.endswith(".gif"):
        return "image/gif"
    return "image/jpeg"


@router.get("/image/{file_id}")
async def get_image(file_id: str):
    if file_id in _cache:
        content, ctype = _cache[file_id]
        return Response(content=content, media_type=ctype, headers={"Cache-Control": "public, max-age=86400"})

    bot = registry.customer_bot or registry.admin_bot or registry.superadmin_bot
    if bot is None:
        raise HTTPException(status_code=503, detail="Bot tayyor emas.")

    try:
        tg_file = await bot.get_file(file_id)
        buffer = await bot.download_file(tg_file.file_path)
        content = buffer.read()
        ctype = _guess_type(tg_file.file_path)
    except Exception as e:
        logger.warning("Rasm yuklab bo'lmadi (%s): %s", file_id, e)
        raise HTTPException(status_code=404, detail="Rasm topilmadi.")

    if len(_cache) < _MAX_CACHE:
        _cache[file_id] = (content, ctype)
    return Response(content=content, media_type=ctype, headers={"Cache-Control": "public, max-age=86400"})

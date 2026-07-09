"""
WebApp xavfsizlik qatlami (IntizomAI patterni asosida).

Himoyalar:
  1. Telegram WebApp `initData` HMAC tekshiruvi — foydalanuvchi haqiqatan o'sha
     telegram_id egasimi (Sotuv bot tokeni bilan tasdiqlanadi). Boshqa odamning
     telegram_id sini qo'lda yuborib ma'lumotini o'qish/o'zgartirish (IDOR) to'siladi.
  2. In-memory rate limiting (DoS/brute-force'ga qarshi).
  3. Xavfsizlik header'lari (XSS, clickjacking, MIME-sniffing).
  4. So'rov hajmi cheklovi.

Mini App Sotuv (Customer) bot orqali ochiladi, shuning uchun HMAC kaliti
BOT_CUSTOMER_TOKEN dan hosil qilinadi.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from urllib.parse import parse_qsl

from fastapi import HTTPException, Request

from core.config import (
    CUSTOMER_BOT_TOKEN,
    INITDATA_MAX_AGE,
    RATE_LIMIT_MAX,
    RATE_LIMIT_WINDOW,
    STRICT_AUTH,
)

logger = logging.getLogger(__name__)


def _secret_key() -> bytes:
    return hmac.new(b"WebAppData", (CUSTOMER_BOT_TOKEN or "").encode(), hashlib.sha256).digest()


def verify_init_data(init_data: str) -> dict | None:
    """initData ni tekshiradi. Muvaffaqiyatda `user` dict qaytaradi, aks holda None.

    Xato sabablari WARNING sifatida loglanadi (Railway loglarida ko'rinadi).
    """
    if not CUSTOMER_BOT_TOKEN:
        logger.warning("initData: BOT_CUSTOMER_TOKEN o'rnatilmagan")
        return None
    if not init_data:
        logger.warning("initData: bo'sh (frontend header/parametr yubormadi)")
        return None
    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", None)
        # Telegram Bot API 7.4+ dan `signature` maydoni qo'shildi (Ed25519 tashqi
        # tekshiruv uchun). U HMAC `data_check_string` ga KIRMAYDI — aks holda
        # hash mos kelmaydi va "Tasdiqlanmagan so'rov" xatosi chiqadi.
        pairs.pop("signature", None)
        if not received_hash:
            logger.warning("initData: hash maydoni yo'q")
            return None

        auth_date = int(pairs.get("auth_date", "0") or "0")
        if auth_date and INITDATA_MAX_AGE > 0:
            if time.time() - auth_date > INITDATA_MAX_AGE:
                logger.warning("initData: eskirgan (auth_date juda eski)")
                return None

        data_check_string = "\n".join(f"{k}={pairs[k]}" for k in sorted(pairs.keys()))
        computed = hmac.new(_secret_key(), data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, received_hash):
            logger.warning("initData: hash mos kelmadi (token noto'g'ri bo'lishi mumkin)")
            return None

        user_raw = pairs.get("user")
        if not user_raw:
            logger.warning("initData: user maydoni yo'q")
            return None
        return json.loads(user_raw)
    except Exception as e:
        logger.warning("initData: tekshirishda xato: %s", e)
        return None


def get_init_data(request: Request) -> str | None:
    """initData ni header'dan, bo'lmasa query parametridan oladi.

    Ba'zi proksi/muhitlar maxsus header'larni olib tashlashi mumkin, shuning uchun
    frontend uni query (`tgWebAppData`) sifatida ham yuboradi — ikkalasi ham qo'llanadi.
    """
    return (
        request.headers.get("x-telegram-init-data")
        or request.query_params.get("tgWebAppData")
        or request.query_params.get("_auth")
    )


def resolve_user(request: Request) -> dict:
    """
    Tasdiqlangan foydalanuvchi (dict: id, first_name, last_name, username...) qaytaradi.
    STRICT_AUTH=true (default) bo'lsa va initData yo'q/yaroqsiz bo'lsa — 401.
    """
    init_data = get_init_data(request)
    user = verify_init_data(init_data or "") if init_data else None
    if user and user.get("id"):
        return user

    if STRICT_AUTH:
        raise HTTPException(status_code=401, detail="Tasdiqlanmagan so'rov. Mini App'ni Telegram orqali oching.")

    # Moslik rejimi (faqat debug uchun) — query'dagi telegram_id.
    try:
        tid = int(request.query_params.get("telegram_id", "0"))
    except (ValueError, TypeError):
        tid = 0
    if tid <= 0:
        raise HTTPException(status_code=401, detail="telegram_id aniqlanmadi.")
    return {"id": tid, "first_name": "User"}


def resolve_telegram_id(request: Request) -> int:
    return int(resolve_user(request)["id"])


# ── In-memory rate limiter ──
_hits: dict[str, list[float]] = {}


def rate_limited(client_key: str) -> bool:
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    bucket = _hits.setdefault(client_key, [])
    while bucket and bucket[0] < window_start:
        bucket.pop(0)
    if len(bucket) >= RATE_LIMIT_MAX:
        return True
    bucket.append(now)
    if len(_hits) > 5000:
        for k in list(_hits.keys()):
            if not _hits[k] or _hits[k][-1] < window_start:
                _hits.pop(k, None)
    return False

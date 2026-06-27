"""Sotuv (Customer) bot kirish nuqtasi."""
from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from core.bots import registry
from core.bots.common import DbSessionMiddleware
from core.bots.customer import handlers
from core.config import CUSTOMER_BOT_TOKEN
from core.database import create_tables

logger = logging.getLogger(__name__)


async def main():
    if not CUSTOMER_BOT_TOKEN:
        logger.warning("ℹ️ BOT_CUSTOMER_TOKEN yo'q — Sotuv bot ishga tushirilmadi.")
        return

    await create_tables()

    bot = Bot(token=CUSTOMER_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    registry.set_customer_bot(bot)

    dp = Dispatcher(storage=MemoryStorage())
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.include_router(handlers.router)

    await bot.set_my_commands([BotCommand(command="start", description="Boshlash / Магазин / Start")])
    logger.info("🚀 Sotuv bot ishga tushdi!")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

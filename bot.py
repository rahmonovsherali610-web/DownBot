"""Asosiy bot fayli - barcha routerlar va middleware larni birlashtirish."""

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import db
from middlewares import (
    RegisterUserMiddleware,
    BanCheckMiddleware,
    MaintenanceMiddleware,
    StateGuardMiddleware,
)
from handlers import (
    start,
    download,
    video_tools,
    audio_tools,
    ai_handler,
    profile,
    help_contact,
    admin,
)

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Bot ishga tushganda."""
    await db.connect()
    me = await bot.get_me()
    logger.info(f"✅ Bot ishga tushdi: @{me.username}")


async def on_shutdown(bot: Bot):
    """Bot to'xtaganda."""
    await db.disconnect()
    logger.info("Bot to'xtatildi.")


async def main():
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN sozlanmagan! .env faylini tekshiring.")
        sys.exit(1)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )

    dp = Dispatcher(storage=MemoryStorage())

    # Middleware larni ro'yxatdan o'tkazish (tartib muhim!)
    dp.message.middleware(RegisterUserMiddleware())
    dp.callback_query.middleware(RegisterUserMiddleware())
    dp.message.middleware(BanCheckMiddleware())
    dp.callback_query.middleware(BanCheckMiddleware())
    dp.message.middleware(MaintenanceMiddleware())
    dp.callback_query.middleware(MaintenanceMiddleware())
    dp.message.middleware(StateGuardMiddleware())
    dp.callback_query.middleware(StateGuardMiddleware())

    # Router larni ro'yxatdan o'tkazish
    dp.include_router(start.router)
    dp.include_router(download.router)
    dp.include_router(video_tools.router)
    dp.include_router(audio_tools.router)
    dp.include_router(ai_handler.router)
    dp.include_router(profile.router)
    dp.include_router(help_contact.router)
    dp.include_router(admin.router)

    # Startup/Shutdown
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("🚀 Bot ishga tushirilmoqda...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot to'xtatildi (KeyboardInterrupt).")

"""Telegramga fayl yuborish - Bot API va MTProto."""

import os
import logging
import asyncio
from typing import Optional

from aiogram import Bot
from aiogram.types import FSInputFile, BufferedInputFile

from config import (
    TELEGRAM_BOT_API_FILE_LIMIT, BOT_TOKEN, API_ID, API_HASH, BOT_USERNAME
)
from utils.helpers import get_file_size_mb

logger = logging.getLogger(__name__)


async def send_video(bot: Bot, chat_id: int, file_path: str,
                     caption: str = "", thumbnail_path: str = None,
                     duration: int = 0, width: int = 0, height: int = 0) -> bool:
    """Video yuborish - hajmiga qarab Bot API yoki MTProto."""
    file_size = os.path.getsize(file_path)

    if not caption:
        caption = f"📥 {BOT_USERNAME} dan yuklab olindi!"

    try:
        if file_size <= TELEGRAM_BOT_API_FILE_LIMIT:
            # Bot API orqali (50MB gacha)
            video = FSInputFile(file_path)
            thumb = FSInputFile(thumbnail_path) if thumbnail_path and os.path.exists(thumbnail_path) else None
            await bot.send_video(
                chat_id=chat_id,
                video=video,
                caption=caption,
                parse_mode="Markdown",
                duration=duration,
                width=width,
                height=height,
                thumbnail=thumb,
                supports_streaming=True,
            )
        else:
            # MTProto orqali (2GB gacha)
            await send_via_mtproto(chat_id, file_path, caption, "video",
                                  thumbnail_path, duration)
        return True
    except Exception as e:
        logger.error(f"Video yuborish xatosi: {e}")
        raise


async def send_audio(bot: Bot, chat_id: int, file_path: str,
                     caption: str = "", thumbnail_path: str = None,
                     title: str = "", performer: str = "",
                     duration: int = 0) -> bool:
    """Audio yuborish."""
    file_size = os.path.getsize(file_path)

    if not caption:
        caption = f"🎵 {BOT_USERNAME} Bot orqali yuklandi."

    try:
        if file_size <= TELEGRAM_BOT_API_FILE_LIMIT:
            audio = FSInputFile(file_path)
            thumb = FSInputFile(thumbnail_path) if thumbnail_path and os.path.exists(thumbnail_path) else None
            await bot.send_audio(
                chat_id=chat_id,
                audio=audio,
                caption=caption,
                parse_mode="Markdown",
                title=title,
                performer=performer,
                duration=duration,
                thumbnail=thumb,
            )
        else:
            await send_via_mtproto(chat_id, file_path, caption, "audio",
                                  thumbnail_path, duration, title, performer)
        return True
    except Exception as e:
        logger.error(f"Audio yuborish xatosi: {e}")
        raise


async def send_document(bot: Bot, chat_id: int, file_path: str,
                        caption: str = "") -> bool:
    """Document (fayl) yuborish."""
    file_size = os.path.getsize(file_path)
    try:
        if file_size <= TELEGRAM_BOT_API_FILE_LIMIT:
            doc = FSInputFile(file_path)
            await bot.send_document(
                chat_id=chat_id,
                document=doc,
                caption=caption,
                parse_mode="Markdown",
            )
        else:
            await send_via_mtproto(chat_id, file_path, caption, "document")
        return True
    except Exception as e:
        logger.error(f"Document yuborish xatosi: {e}")
        raise


async def send_via_mtproto(chat_id: int, file_path: str, caption: str,
                           media_type: str, thumbnail_path: str = None,
                           duration: int = 0, title: str = "",
                           performer: str = ""):
    """Pyrogram (MTProto) orqali katta fayllarni yuborish."""
    try:
        from pyrogram import Client
        from pyrogram.types import InputMediaVideo, InputMediaAudio

        # Pyrogram clientni ishga tushirish
        app = Client(
            "bot_mtproto",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workdir=str(os.path.dirname(os.path.abspath(__file__))),
        )

        async with app:
            if media_type == "video":
                await app.send_video(
                    chat_id=chat_id,
                    video=file_path,
                    caption=caption,
                    parse_mode=None,
                    duration=duration,
                    thumb=thumbnail_path,
                    supports_streaming=True,
                )
            elif media_type == "audio":
                await app.send_audio(
                    chat_id=chat_id,
                    audio=file_path,
                    caption=caption,
                    parse_mode=None,
                    duration=duration,
                    title=title,
                    performer=performer,
                    thumb=thumbnail_path,
                )
            else:
                await app.send_document(
                    chat_id=chat_id,
                    document=file_path,
                    caption=caption,
                    parse_mode=None,
                )

        logger.info(f"MTProto orqali yuborildi: {file_path}")
    except ImportError:
        raise RuntimeError("Pyrogram o'rnatilmagan! pip install pyrogram tgcrypto")
    except Exception as e:
        logger.error(f"MTProto yuborish xatosi: {e}")
        raise RuntimeError(f"Katta fayl yuborishda xatolik: {e}")

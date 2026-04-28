"""Dinamik progress bar va jarayon boshqarish."""

import time
import asyncio
import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import Message
from aiogram.exceptions import TelegramBadRequest

from config import PROGRESS_UPDATE_INTERVAL

logger = logging.getLogger(__name__)


def make_progress_bar(percent: float, length: int = 10) -> str:
    """Chiroyli progress bar yasash."""
    filled = int(length * percent / 100)
    bar = "▬" * filled + "▭" * (length - filled)
    return bar


class ProgressTracker:
    """Dinamik progress bar bilan xabarni yangilab turish."""

    def __init__(self, bot: Bot, chat_id: int, action: str = "Yuklanmoqda"):
        self.bot = bot
        self.chat_id = chat_id
        self.action = action
        self.message: Optional[Message] = None
        self.last_update_time: float = 0
        self.last_percent: int = -1
        self._cancelled = False

    async def start(self) -> Message:
        """Jarayon boshlanishi xabarini yuborish."""
        text = f"⏳ {self.action}...\n📥 0% [{make_progress_bar(0)}]"
        self.message = await self.bot.send_message(self.chat_id, text)
        self.last_update_time = time.time()
        return self.message

    async def update(self, percent: float, extra: str = ""):
        """Progress ni yangilash (har 2 soniyada)."""
        if self._cancelled:
            return
        now = time.time()
        int_percent = int(percent)
        # Faqat 2 soniyadan keyin va foiz o'zgarganda yangilash
        if (now - self.last_update_time < PROGRESS_UPDATE_INTERVAL
                and int_percent == self.last_percent):
            return

        self.last_update_time = now
        self.last_percent = int_percent
        bar = make_progress_bar(percent)
        text = f"⏳ {self.action}...\n📥 {int_percent}% [{bar}]"
        if extra:
            text += f"\n{extra}"

        if self.message:
            try:
                await self.message.edit_text(text)
            except TelegramBadRequest:
                pass  # Xabar o'zgarmaganligi (message is not modified)
            except Exception as e:
                logger.debug(f"Progress update xatosi: {e}")

    async def finish(self, success_text: str = "✅ Bajarildi!"):
        """Jarayon tugashi va progress xabarini o'chirish."""
        self._cancelled = True
        if self.message:
            try:
                await self.message.edit_text(success_text)
                # 3 soniyadan keyin xabarni o'chirish
                await asyncio.sleep(3)
                await self.message.delete()
            except Exception:
                pass

    async def error(self, error_text: str):
        """Xatolik xabari."""
        self._cancelled = True
        if self.message:
            try:
                await self.message.edit_text(f"❌ {error_text}")
            except Exception:
                pass

    async def delete(self):
        """Progress xabarini o'chirish."""
        if self.message:
            try:
                await self.message.delete()
            except Exception:
                pass

    def cancel(self):
        self._cancelled = True


def yt_dlp_progress_hook(tracker: ProgressTracker, loop: asyncio.AbstractEventLoop):
    """yt-dlp uchun progress hook."""
    def hook(d):
        if d["status"] == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            if total > 0:
                percent = (downloaded / total) * 100
                speed = d.get("speed")
                speed_str = ""
                if speed:
                    speed_mb = speed / (1024 * 1024)
                    speed_str = f"⚡ {speed_mb:.1f} MB/s"
                asyncio.run_coroutine_threadsafe(
                    tracker.update(percent, speed_str), loop
                )
        elif d["status"] == "finished":
            asyncio.run_coroutine_threadsafe(
                tracker.update(100, "📦 Qayta ishlash..."), loop
            )
    return hook

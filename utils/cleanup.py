"""Vaqtinchalik fayllarni avtomatik tozalash."""

import os
import asyncio
import logging
from pathlib import Path

from config import TEMP_DIR

logger = logging.getLogger(__name__)


async def safe_remove(filepath: str, delay: float = 5.0):
    """Faylni xavfsiz o'chirish (delay bilan)."""
    try:
        await asyncio.sleep(delay)
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"🗑 Vaqtinchalik fayl o'chirildi: {filepath}")
    except Exception as e:
        logger.warning(f"Fayl o'chirish xatosi: {filepath} - {e}")


async def cleanup_files(*filepaths: str, delay: float = 7.0):
    """Bir nechta fayllarni tozalash."""
    for fp in filepaths:
        if fp and os.path.exists(fp):
            asyncio.create_task(safe_remove(fp, delay))


async def cleanup_temp_dir():
    """Butun temp papkani tozalash."""
    try:
        count = 0
        for f in TEMP_DIR.iterdir():
            if f.is_file():
                f.unlink()
                count += 1
            elif f.is_dir():
                import shutil
                shutil.rmtree(f, ignore_errors=True)
                count += 1
        logger.info(f"🧹 Temp papka tozalandi: {count} ta fayl o'chirildi")
        return count
    except Exception as e:
        logger.error(f"Temp papka tozalash xatosi: {e}")
        return 0


def get_temp_path(filename: str) -> str:
    """Vaqtinchalik fayl yo'lini olish."""
    return str(TEMP_DIR / filename)


def get_temp_dir_size() -> float:
    """Temp papka hajmini MB da qaytarish."""
    total = 0
    try:
        for f in TEMP_DIR.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    except Exception:
        pass
    return total / (1024 * 1024)

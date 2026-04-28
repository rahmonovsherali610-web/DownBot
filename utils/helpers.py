"""Yordamchi funksiyalar."""

import re
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def is_valid_url(text: str) -> bool:
    """URL validatsiyasi."""
    url_pattern = re.compile(
        r"https?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"
        r"(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)",
        re.IGNORECASE,
    )
    return bool(url_pattern.match(text.strip()))


def detect_platform(url: str) -> str:
    """URL dan platformani aniqlash."""
    url = url.lower()
    platforms = {
        "youtube.com": "YouTube", "youtu.be": "YouTube",
        "tiktok.com": "TikTok",
        "instagram.com": "Instagram",
        "facebook.com": "Facebook", "fb.watch": "Facebook",
        "twitter.com": "Twitter/X", "x.com": "Twitter/X",
        "pinterest.com": "Pinterest",
        "vimeo.com": "Vimeo",
        "dailymotion.com": "Dailymotion",
        "soundcloud.com": "SoundCloud",
        "twitch.tv": "Twitch",
        "reddit.com": "Reddit",
        "bilibili.com": "Bilibili",
    }
    for domain, name in platforms.items():
        if domain in url:
            return name
    return "Noma'lum platforma"


def format_duration(seconds: int) -> str:
    """Soniyani soat:daqiqa:soniya formatiga o'tkazish."""
    if not seconds:
        return "00:00"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_size(size_bytes: int) -> str:
    """Baytni MB/GB formatiga o'tkazish."""
    if not size_bytes:
        return "N/A"
    mb = size_bytes / (1024 * 1024)
    if mb >= 1024:
        return f"{mb / 1024:.2f} GB"
    return f"{mb:.1f} MB"


def parse_time_range(text: str) -> Optional[tuple[str, str]]:
    """Vaqt oralig'ini parse qilish. Masalan: 00:10 - 00:45"""
    text = text.strip().replace("–", "-").replace("—", "-")
    pattern = r"(\d{1,2}:\d{2}(?::\d{2})?)\s*-\s*(\d{1,2}:\d{2}(?::\d{2})?)"
    match = re.match(pattern, text)
    if match:
        return match.group(1), match.group(2)
    return None


def time_to_seconds(time_str: str) -> int:
    """Vaqt stringini soniyaga o'tkazish. Masalan: 01:30 -> 90"""
    parts = time_str.strip().split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    elif len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0


def get_file_size_mb(filepath: str) -> float:
    """Fayl hajmini MB da qaytarish."""
    try:
        return os.path.getsize(filepath) / (1024 * 1024)
    except Exception:
        return 0.0


def sanitize_filename(name: str, max_length: int = 60) -> str:
    """Fayl nomini tozalash."""
    # Maxsus belgilarni o'chirish
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.strip(). replace('\n', ' ')
    if len(name) > max_length:
        name = name[:max_length]
    return name or "media"

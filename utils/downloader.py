"""yt-dlp orqali video/audio yuklab olish."""

import os
import asyncio
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

import yt_dlp

from config import YT_DLP_OPTIONS, TEMP_DIR, QUALITY_LABELS
from utils.helpers import format_duration, format_size, detect_platform, sanitize_filename

logger = logging.getLogger(__name__)
executor = ThreadPoolExecutor(max_workers=3)


async def get_media_info(url: str) -> Optional[dict]:
    """Video/audio haqida ma'lumot olish."""
    try:
        opts = {
            **YT_DLP_OPTIONS,
            "skip_download": True,
            "no_playlist": True,
        }
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(
            executor,
            lambda: yt_dlp.YoutubeDL(opts).extract_info(url, download=False)
        )
        if not info:
            return None

        duration = info.get("duration", 0)
        thumbnail = info.get("thumbnail", "")
        # Eng yaxshi thumbnail tanlash
        thumbs = info.get("thumbnails", [])
        if thumbs:
            best_thumb = max(thumbs, key=lambda t: t.get("width", 0) * t.get("height", 0))
            thumbnail = best_thumb.get("url", thumbnail)

        return {
            "title": info.get("title", "Nomsiz"),
            "uploader": info.get("uploader", info.get("channel", "Noma'lum")),
            "duration": duration,
            "duration_str": format_duration(duration),
            "thumbnail": thumbnail,
            "url": url,
            "platform": detect_platform(url),
            "formats": info.get("formats", []),
            "webpage_url": info.get("webpage_url", url),
            "id": info.get("id", ""),
            "filesize_approx": info.get("filesize_approx", 0),
        }
    except yt_dlp.utils.DownloadError as e:
        err_msg = str(e)
        if "Unsupported URL" in err_msg:
            raise ValueError("❌ Bu havola qo'llab-quvvatlanmaydi!")
        elif "Video unavailable" in err_msg:
            raise ValueError("❌ Video mavjud emas yoki o'chirilgan!")
        elif "Private video" in err_msg:
            raise ValueError("🔒 Bu video shaxsiy (private)!")
        elif "Sign in" in err_msg or "login" in err_msg.lower():
            raise ValueError("🔐 Bu videoni ko'rish uchun tizimga kirish talab etiladi!")
        elif "blocked" in err_msg.lower() or "403" in err_msg:
            raise ValueError("🚫 IP bloklangan yoki video cheklangan! Proxy tekshiring.")
        else:
            raise ValueError(f"❌ Xatolik: {err_msg[:200]}")
    except Exception as e:
        logger.error(f"Media info xatosi: {e}")
        raise ValueError(f"❌ Ma'lumot olishda xatolik: {str(e)[:200]}")


def extract_video_formats(formats: list) -> list[dict]:
    """Mavjud video sifatlarini ajratib olish."""
    seen = {}
    for f in formats:
        vcodec = f.get("vcodec", "none")
        height = f.get("height")
        if vcodec == "none" or not height:
            continue

        key = height
        filesize = f.get("filesize") or f.get("filesize_approx") or 0
        fps = f.get("fps", 0)
        format_id = f.get("format_id", "")
        acodec = f.get("acodec", "none")

        if key not in seen or (filesize > 0 and filesize > seen[key].get("filesize", 0)):
            label = QUALITY_LABELS.get(str(height), f"{height}p")
            seen[key] = {
                "format_id": format_id,
                "height": height,
                "fps": fps,
                "filesize": filesize,
                "size_mb": filesize / (1024 * 1024) if filesize else 0,
                "label": f"{height}p ({label})",
                "has_audio": acodec != "none",
                "ext": f.get("ext", "mp4"),
            }

    result = sorted(seen.values(), key=lambda x: x["height"])
    # Agar hajmi noma'lum bo'lsa, taxminiy hisoblash
    for r in result:
        if r["size_mb"] == 0:
            # Taxminiy: 1 daqiqa 720p ~= 50MB
            base_rate = {144: 2, 240: 4, 360: 8, 480: 15, 720: 30,
                         1080: 60, 1440: 100, 2160: 200, 4320: 500}
            rate = base_rate.get(r["height"], 30)
            r["size_mb"] = rate  # Taxminiy
    return result


def extract_audio_formats(formats: list, duration: int = 0) -> list[dict]:
    """Mavjud audio formatlarini ajratib olish."""
    audio_options = []
    best_abr = 0
    for f in formats:
        abr = f.get("abr") or f.get("tbr", 0)
        if abr and abr > best_abr:
            best_abr = abr

    if not best_abr:
        best_abr = 128

    targets = [
        {"ext": "wav", "quality": "Juda yuqori sifat", "codec": "pcm_s16le", "abr": best_abr},
        {"ext": "m4a", "quality": "Yuqori sifat", "codec": "aac", "abr": min(best_abr, 256)},
        {"ext": "mp3", "quality": "Yaxshi sifat", "codec": "libmp3lame", "abr": min(best_abr, 320)},
        {"ext": "ogg", "quality": "Telegram Voice", "codec": "libopus", "abr": min(best_abr, 128)},
    ]

    for t in targets:
        size_estimate = 0
        if duration > 0:
            if t["ext"] == "wav":
                size_estimate = duration * 176400 / (1024 * 1024)  # 44100*2*2
            else:
                size_estimate = duration * t["abr"] * 1000 / 8 / (1024 * 1024)
        audio_options.append({
            "format_id": t["ext"],
            "ext": t["ext"],
            "quality": t["quality"],
            "size_mb": round(size_estimate, 1),
            "codec": t["codec"],
            "abr": t["abr"],
        })
    return audio_options


async def download_video(url: str, format_id: str, output_path: str,
                         progress_hook=None) -> str:
    """Video yuklab olish (audio bilan)."""
    try:
        opts = {
            **YT_DLP_OPTIONS,
            "format": f"{format_id}+bestaudio/best",
            "outtmpl": output_path,
            "merge_output_format": "mp4",
            "postprocessors": [{
                "key": "FFmpegVideoConvertor",
                "preferedformat": "mp4",
            }],
            "no_playlist": True,
        }
        if progress_hook:
            opts["progress_hooks"] = [progress_hook]

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            executor,
            lambda: yt_dlp.YoutubeDL(opts).download([url])
        )

        # Chiqish faylini topish
        base = os.path.splitext(output_path)[0]
        for ext in [".mp4", ".mkv", ".webm"]:
            if os.path.exists(base + ext):
                return base + ext
        return output_path
    except Exception as e:
        logger.error(f"Video yuklab olish xatosi: {e}")
        raise ValueError(f"❌ Video yuklab olishda xatolik: {str(e)[:200]}")


async def download_audio(url: str, audio_format: str, output_path: str,
                         progress_hook=None) -> str:
    """Audio yuklab olish."""
    try:
        codec_map = {"mp3": "mp3", "m4a": "m4a", "ogg": "vorbis",
                     "wav": "wav", "flac": "flac"}
        preferred = codec_map.get(audio_format, "mp3")

        opts = {
            **YT_DLP_OPTIONS,
            "format": "bestaudio/best",
            "outtmpl": output_path,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": preferred,
                "preferredquality": "0",
            }],
            "writethumbnail": True,
            "no_playlist": True,
        }
        if progress_hook:
            opts["progress_hooks"] = [progress_hook]

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            executor,
            lambda: yt_dlp.YoutubeDL(opts).download([url])
        )

        base = os.path.splitext(output_path)[0]
        for ext in [f".{audio_format}", ".mp3", ".m4a", ".ogg", ".wav", ".flac"]:
            if os.path.exists(base + ext):
                return base + ext
        return output_path
    except Exception as e:
        logger.error(f"Audio yuklab olish xatosi: {e}")
        raise ValueError(f"❌ Audio yuklab olishda xatolik: {str(e)[:200]}")


async def download_thumbnail(url: str, output_path: str) -> Optional[str]:
    """Thumbnail yuklab olish."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    with open(output_path, "wb") as f:
                        f.write(data)
                    return output_path
        return None
    except Exception as e:
        logger.error(f"Thumbnail yuklab olish xatosi: {e}")
        return None

"""Bot konfiguratsiya fayli. Barcha sozlamalar .env faylidan o'qiladi."""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ===== Bot sozlamalari =====
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
BOT_USERNAME: str = os.getenv("BOT_USERNAME", "@bot")

# ===== Admin sozlamalari =====
ADMIN_IDS: list[int] = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "0").split(",") if x.strip()]
ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "@admin")

# ===== Ma'lumotlar bazasi =====
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/telegram_bot")

# ===== DeepSeek AI =====
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# ===== Pyrogram (MTProto) katta fayllar uchun =====
API_ID: int = int(os.getenv("API_ID", "0"))
API_HASH: str = os.getenv("API_HASH", "")

# ===== yt-dlp Proxy =====
YT_DLP_PROXY: str = os.getenv("YT_DLP_PROXY", "")

# ===== Saqlash =====
SAVE_CHAT_ID: int = int(os.getenv("SAVE_CHAT_ID", "0"))

# ===== Vaqtinchalik fayllar =====
TEMP_DIR: Path = Path(os.getenv("TEMP_DIR", "./temp"))
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# ===== Telegram limitlari =====
TELEGRAM_BOT_API_FILE_LIMIT = 50 * 1024 * 1024  # 50 MB
TELEGRAM_MTPROTO_FILE_LIMIT = 2 * 1024 * 1024 * 1024  # 2 GB

# ===== Maintenance rejimi =====
MAINTENANCE_MODE: bool = False

# ===== Progress bar sozlamalari =====
PROGRESS_UPDATE_INTERVAL: float = 2.0  # soniya

# ===== yt-dlp sozlamalari =====
YT_DLP_OPTIONS: dict = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
    "socket_timeout": 30,
    "retries": 3,
    "fragment_retries": 3,
    "http_headers": {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    },
}

# Proxy qo'shish (agar mavjud bo'lsa)
if YT_DLP_PROXY:
    YT_DLP_OPTIONS["proxy"] = YT_DLP_PROXY

# ===== Sifat nomlari =====
QUALITY_LABELS: dict[str, str] = {
    "144": "Eng Past Sifatli!",
    "240": "Pastroq sifatli!",
    "360": "O'rta sifatli!",
    "480": "SD-Yuqori sifatli",
    "720": "HD",
    "1080": "Full HD",
    "1440": "2K / QHD",
    "2160": "4K UHD",
    "4320": "8K UHD",
}

# ===== Audio format kodeklari =====
AUDIO_CODECS: dict[str, str] = {
    "mp3": "libmp3lame",
    "m4a": "aac",
    "ogg": "libopus",
    "flac": "flac",
    "wav": "pcm_s16le",
}

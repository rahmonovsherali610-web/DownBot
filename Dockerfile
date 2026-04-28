# ============================================================
#  Telegram Bot — Railway Deployment Dockerfile
#  Stack: Python 3.11 · aiogram 3 · FFmpeg · PostgreSQL (asyncpg)
#         yt-dlp · Pyrogram (MTProto) · DeepSeek AI
# ============================================================

# ── Stage 1: Builder ─────────────────────────────────────────
FROM python:3.11-slim-bookworm AS builder

# Build vaqtida kerak bo'ladigan paketlar
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .

# Wheel larni build qilish (runtime stage da faqat shu wheellarni o'rnatamiz)
RUN pip install --upgrade pip \
 && pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# ── Stage 2: Runtime ─────────────────────────────────────────
FROM python:3.11-slim-bookworm AS runtime

# ── Tizim paketlari ──────────────────────────────────────────
# ffmpeg: barcha media kodeklar bilan to'liq o'rnatiladi
#   - ffmpeg  : video/audio konvertatsiya, kesish, birlashtirish
#   - ffprobe : media fayl ma'lumotlarini o'qish (davomiylik, o'lcham, kodek)
# Kodeklar (Debian Bookworm ffmpeg paketida mavjud):
#   - libmp3lame (mp3), libopus (ogg/opus), libvorbis (ogg),
#     libx264 (h264), libx265 (h265), libvpx (webm),
#     aac (m4a), flac, pcm_s16le (wav) — barchasi shu bot uchun kerak
RUN apt-get update && apt-get install -y --no-install-recommends \
        # ─ FFmpeg (to'liq kodek to'plami bilan) ─
        ffmpeg \
        # ─ PostgreSQL client kutubxonasi (asyncpg uchun) ─
        libpq5 \
        # ─ Tarmoq va fayl utilitalari ─
        ca-certificates \
        curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# FFmpeg to'g'ri o'rnatilganligini tekshirish (build vaqtida)
RUN ffmpeg -version | head -n1 \
 && ffprobe -version | head -n1

# ── Python paketlar ──────────────────────────────────────────
# Builder stage dan tayyor wheel larni nusxalaymiz
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links /wheels /wheels/*.whl \
 && rm -rf /wheels

# ── Ilova kodi ───────────────────────────────────────────────
WORKDIR /app

COPY . .

# ── Kataloglar va ruxsatlar ───────────────────────────────────
# /app/temp  — yt-dlp, ffmpeg vaqtinchalik fayllar uchun
# /app/logs  — bot.log uchun
# /app/utils — Pyrogram session fayli shu joyda yaratiladi
RUN mkdir -p /app/temp /app/logs \
 && chmod 777 /app/temp /app/logs

# ── Xavfsizlik: root bo'lmagan foydalanuvchi ─────────────────
RUN groupadd --gid 1001 botuser \
 && useradd --uid 1001 --gid 1001 --no-create-home botuser \
 && chown -R botuser:botuser /app

USER botuser

# ── Muhit o'zgaruvchilari ─────────────────────────────────────
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # Temp papka yo'li (config.py da TEMP_DIR ga override)
    TEMP_DIR=/app/temp \
    # Python path
    PYTHONPATH=/app \
    # Pyrogram session fayllar joyi
    PYROGRAM_SESSION_DIR=/app

# ── Sog'lom tekshiruv ─────────────────────────────────────────
# Railway botni tirik yoki o'lik ekanini bilish uchun ishlatadi.
# Polling bot bo'lgani uchun HTTP port yo'q — process tirikligini tekshiramiz.
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD pgrep -f "python bot.py" > /dev/null || exit 1

# ── Ishga tushirish ───────────────────────────────────────────
# Railway polling rejimida ishlaydi — EXPOSE kerak emas
CMD ["python", "bot.py"]

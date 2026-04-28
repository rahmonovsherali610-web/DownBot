# 🤖 Professional Telegram Media Bot

Professional darajadagi video va audio yuklab oluvchi Telegram bot.

## Xususiyatlar

- 🔗 **Havola orqali yuklash** - YouTube, TikTok, Instagram va 1000+ saytdan
- 🛠 **Media asboblar** - Video/Audio kesish, effektlar, format o'zgartirish
- 🤖 **AI yordamchi** - DeepSeek API integratsiyasi
- 👤 **Profil** - Foydalanuvchi ma'lumotlari
- ⚙️ **Admin panel** - Ban, broadcast, server monitoring

## O'rnatish

### 1. Talablar
- Python 3.11+
- PostgreSQL
- ffmpeg (PATH da bo'lishi kerak)
- yt-dlp

### 2. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. ffmpeg o'rnatish
Windows: `winget install ffmpeg` yoki https://ffmpeg.org/download.html
Linux: `sudo apt install ffmpeg`

### 4. Sozlash
```bash
cp .env.example .env
# .env faylini to'ldiring
```

### 5. PostgreSQL bazasini yaratish
```sql
CREATE DATABASE telegram_bot;
```

### 6. Ishga tushirish
```bash
python bot.py
```

## Loyiha tuzilishi
```
telegram_bot/
├── bot.py              # Asosiy entry point
├── config.py           # Konfiguratsiya
├── database.py         # PostgreSQL
├── states.py           # FSM holatlari
├── keyboards.py        # Inline klaviaturalar
├── middlewares.py       # Middleware
├── handlers/           # Barcha handlerlar
│   ├── start.py
│   ├── download.py
│   ├── video_tools.py
│   ├── audio_tools.py
│   ├── ai_handler.py
│   ├── profile.py
│   ├── help_contact.py
│   └── admin.py
└── utils/              # Yordamchi modullar
    ├── downloader.py
    ├── media_processor.py
    ├── progress.py
    ├── cleanup.py
    ├── uploader.py
    └── helpers.py
```

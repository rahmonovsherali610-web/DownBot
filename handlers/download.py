"""Havola orqali yuklab olish handleri (A bo'limi)."""

import os
import asyncio
import logging
import uuid

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

from states import DownloadStates
from keyboards import (
    media_info_kb, video_quality_kb, audio_format_kb,
    main_menu_kb, back_and_cancel,
)
from config import TEMP_DIR, BOT_USERNAME, SAVE_CHAT_ID
from utils.downloader import (
    get_media_info, extract_video_formats, extract_audio_formats,
    download_video, download_audio, download_thumbnail,
)
from utils.progress import ProgressTracker, yt_dlp_progress_hook
from utils.uploader import send_video, send_audio
from utils.cleanup import cleanup_files
from utils.helpers import (
    is_valid_url, format_duration, format_size,
    sanitize_filename, get_file_size_mb,
)
from database import db

logger = logging.getLogger(__name__)
router = Router(name="download")


@router.callback_query(F.data == "download_link")
async def start_download(callback: CallbackQuery, state: FSMContext):
    """Havola orqali yuklash bo'limi."""
    await state.set_state(DownloadStates.waiting_for_link)
    text = (
        "🔗 *Havola orqali yuklash*\n\n"
        "📌 Quyidagi imkoniyatlar:\n"
        "• 🎬 Video yuklab olish (barcha sifatlarda)\n"
        "• 🎵 Audio yuklab olish\n"
        "• 🎶 To'liq musiqani topish\n\n"
        "🌐 Qo'llab-quvvatlanadigan platformalar:\n"
        "YouTube, TikTok, Instagram, Facebook, Twitter/X, "
        "Pinterest, SoundCloud, Vimeo va 1000+ sayt\n\n"
        "👇 *Havola yuboring:*"
    )
    await callback.message.edit_text(text, parse_mode="Markdown")
    await callback.answer()


@router.message(DownloadStates.waiting_for_link)
async def process_link(message: Message, state: FSMContext, bot: Bot):
    """Yuborilgan havolani qayta ishlash."""
    url = message.text.strip() if message.text else ""

    if not url or not is_valid_url(url):
        await message.answer(
            "⚠️ Iltimos, faqat havola (link) yuboring!\n"
            "Masalan: `https://youtube.com/watch?v=...`",
            parse_mode="Markdown",
        )
        return

    progress = ProgressTracker(bot, message.chat.id, "Ma'lumot olinmoqda")
    await progress.start()

    try:
        info = await get_media_info(url)
        if not info:
            await progress.error("Ma'lumot olishda xatolik yuz berdi!")
            return

        # Ma'lumotlarni state ga saqlash
        await state.update_data(
            url=url,
            title=info["title"],
            uploader=info["uploader"],
            duration=info["duration"],
            duration_str=info["duration_str"],
            thumbnail=info["thumbnail"],
            platform=info["platform"],
            formats=info["formats"],
            media_id=info["id"],
        )

        # Thumbnail yuborish
        thumb_path = None
        if info["thumbnail"]:
            thumb_path = str(TEMP_DIR / f"thumb_{uuid.uuid4().hex[:8]}.jpg")
            thumb_path = await download_thumbnail(info["thumbnail"], thumb_path)

        if thumb_path and os.path.exists(thumb_path):
            await bot.send_photo(
                message.chat.id,
                FSInputFile(thumb_path),
                caption="🖼 *Thumbnail*",
                parse_mode="Markdown",
            )
            asyncio.create_task(cleanup_files(thumb_path, delay=30))

        # Hajmni hisoblash
        video_formats = extract_video_formats(info["formats"])
        best_size = max((f["size_mb"] for f in video_formats), default=0)

        info_text = (
            f"📹 *Video ma'lumotlari:*\n\n"
            f"📌 *Nomi:* {info['title']}\n"
            f"👤 *Muallif:* {info['uploader']}\n"
            f"⏱ *Davomiyligi:* {info['duration_str']}\n"
            f"📦 *Taxminiy hajmi:* ~{best_size:.1f} MB\n"
            f"🌐 *Platforma:* {info['platform']}\n"
        )

        await progress.delete()
        await state.set_state(DownloadStates.showing_info)
        await message.answer(
            info_text,
            reply_markup=media_info_kb(),
            parse_mode="Markdown",
        )

    except ValueError as e:
        await progress.error(str(e))
        await state.set_state(DownloadStates.waiting_for_link)
    except Exception as e:
        logger.error(f"Link qayta ishlash xatosi: {e}")
        await progress.error(f"Kutilmagan xatolik: {str(e)[:200]}")
        await state.set_state(DownloadStates.waiting_for_link)


@router.callback_query(F.data == "dl_video", DownloadStates.showing_info)
async def choose_video_quality(callback: CallbackQuery, state: FSMContext):
    """Video sifat tanlash."""
    data = await state.get_data()
    formats = data.get("formats", [])
    video_formats = extract_video_formats(formats)

    if not video_formats:
        await callback.answer("❌ Video formatlari topilmadi!", show_alert=True)
        return

    await state.update_data(video_formats=video_formats)
    await state.set_state(DownloadStates.choosing_video_quality)
    await callback.message.edit_text(
        "📹 *Video sifatini tanlang:*\n\n"
        "⚠️ 50 MB dan katta fayllar MTProto orqali yuboriladi.",
        reply_markup=video_quality_kb(video_formats),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("vq_"), DownloadStates.choosing_video_quality)
async def download_video_quality(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Tanlangan sifatda video yuklab olish."""
    format_id = callback.data.replace("vq_", "")
    data = await state.get_data()
    url = data.get("url")
    title = sanitize_filename(data.get("title", "video"))
    duration = data.get("duration", 0)

    await state.set_state(DownloadStates.downloading)
    await callback.answer()

    output_path = str(TEMP_DIR / f"{uuid.uuid4().hex[:8]}_{title}.%(ext)s")
    progress = ProgressTracker(bot, callback.message.chat.id, "Video yuklanmoqda")
    await progress.start()

    downloaded_file = None
    thumb_path = None
    try:
        loop = asyncio.get_event_loop()
        hook = yt_dlp_progress_hook(progress, loop)

        downloaded_file = await download_video(url, format_id, output_path, hook)

        await progress.update(100, "📤 Telegramga yuborilmoqda...")
        await state.set_state(DownloadStates.uploading)

        # Thumbnail
        thumbnail_url = data.get("thumbnail", "")
        if thumbnail_url:
            thumb_path = str(TEMP_DIR / f"vthumb_{uuid.uuid4().hex[:8]}.jpg")
            thumb_path = await download_thumbnail(thumbnail_url, thumb_path)

        caption = (
            f"📥 *{BOT_USERNAME}* dan yuklab olindi!\n\n"
            f"📹 *{data.get('title', 'Video')}*\n"
            f"⏱ Davomiyligi: {data.get('duration_str', 'N/A')}"
        )

        from utils.media_processor import get_video_resolution
        w, h = await get_video_resolution(downloaded_file)

        await send_video(
            bot, callback.message.chat.id, downloaded_file,
            caption=caption, thumbnail_path=thumb_path,
            duration=duration, width=w, height=h,
        )

        await progress.finish("✅ Video muvaffaqiyatli yuborildi!")
        await db.log_download(callback.from_user.id, url, "video", format_id)

        # Yuklanganidan keyingi tugmalar (Video o'chiriladi, Saqlash va Orqaga qoladi)
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        post_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎵 Audio", callback_data="dl_audio")],
            [InlineKeyboardButton(text="💾 Saqlash", callback_data="dl_save")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back")],
        ])
        await state.set_state(DownloadStates.showing_info)
        await callback.message.answer(
            "✅ Yana nimani yuklamoqchisiz?",
            reply_markup=post_kb,
        )

    except Exception as e:
        logger.error(f"Video yuklash xatosi: {e}")
        await progress.error(f"Video yuklashda xatolik:\n{str(e)[:300]}")
        await state.set_state(DownloadStates.showing_info)
    finally:
        await cleanup_files(downloaded_file, thumb_path, delay=7)


@router.callback_query(F.data == "dl_audio", DownloadStates.showing_info)
async def choose_audio_format(callback: CallbackQuery, state: FSMContext):
    """Audio format tanlash."""
    data = await state.get_data()
    formats = data.get("formats", [])
    duration = data.get("duration", 0)
    audio_formats = extract_audio_formats(formats, duration)

    await state.update_data(audio_formats=audio_formats)
    await state.set_state(DownloadStates.choosing_audio_format)
    await callback.message.edit_text(
        "🎵 *Audio formatini tanlang:*\n\n"
        "🖼 Thumbnail audioga avtomatik biriktiriladi.",
        reply_markup=audio_format_kb(audio_formats),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("af_"), DownloadStates.choosing_audio_format)
async def download_audio_format(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Tanlangan formatda audio yuklab olish."""
    audio_fmt = callback.data.replace("af_", "")
    data = await state.get_data()
    url = data.get("url")
    title = sanitize_filename(data.get("title", "audio"))
    duration = data.get("duration", 0)

    await state.set_state(DownloadStates.downloading)
    await callback.answer()

    output_path = str(TEMP_DIR / f"{uuid.uuid4().hex[:8]}_{title}.%(ext)s")
    progress = ProgressTracker(bot, callback.message.chat.id, "Audio yuklanmoqda")
    await progress.start()

    downloaded_file = None
    thumb_path = None
    try:
        loop = asyncio.get_event_loop()
        hook = yt_dlp_progress_hook(progress, loop)

        downloaded_file = await download_audio(url, audio_fmt, output_path, hook)

        await progress.update(100, "📤 Telegramga yuborilmoqda...")
        await state.set_state(DownloadStates.uploading)

        # Thumbnail
        thumbnail_url = data.get("thumbnail", "")
        if thumbnail_url:
            thumb_path = str(TEMP_DIR / f"athumb_{uuid.uuid4().hex[:8]}.jpg")
            thumb_path = await download_thumbnail(thumbnail_url, thumb_path)

        # Thumbnail ni audioga embed qilish
        if thumb_path and os.path.exists(thumb_path):
            try:
                from utils.media_processor import run_ffmpeg
                embedded_path = downloaded_file + ".embedded" + os.path.splitext(downloaded_file)[1]
                await run_ffmpeg([
                    "-i", downloaded_file, "-i", thumb_path,
                    "-map", "0:a", "-map", "1:0",
                    "-c", "copy", "-disposition:v", "attached_pic",
                    embedded_path,
                ])
                if os.path.exists(embedded_path):
                    os.replace(embedded_path, downloaded_file)
            except Exception as e:
                logger.warning(f"Thumbnail embed xatosi: {e}")

        caption = (
            f"🎵 *{BOT_USERNAME}* Bot orqali yuklandi.\n\n"
            f"🎵 *{data.get('title', 'Audio')}*\n"
            f"⏱ Davomiyligi: {data.get('duration_str', 'N/A')}"
        )

        await send_audio(
            bot, callback.message.chat.id, downloaded_file,
            caption=caption, thumbnail_path=thumb_path,
            title=data.get("title", ""), performer=data.get("uploader", ""),
            duration=duration,
        )

        await progress.finish("✅ Audio muvaffaqiyatli yuborildi!")
        await db.log_download(callback.from_user.id, url, "audio", audio_fmt)

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        post_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎬 Video", callback_data="dl_video")],
            [InlineKeyboardButton(text="💾 Saqlash", callback_data="dl_save")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back")],
        ])
        await state.set_state(DownloadStates.showing_info)
        await callback.message.answer(
            "✅ Yana nimani yuklamoqchisiz?",
            reply_markup=post_kb,
        )

    except Exception as e:
        logger.error(f"Audio yuklash xatosi: {e}")
        await progress.error(f"Audio yuklashda xatolik:\n{str(e)[:300]}")
        await state.set_state(DownloadStates.showing_info)
    finally:
        await cleanup_files(downloaded_file, thumb_path, delay=7)


@router.callback_query(F.data == "dl_save")
async def save_media(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Medianii saqlash chatiga uzatish."""
    try:
        if not SAVE_CHAT_ID:
            await callback.answer("⚠️ Saqlash chat ID sozlanmagan!", show_alert=True)
            return

        # Oxirgi xabarni forward qilish
        if callback.message.reply_to_message:
            await callback.message.reply_to_message.forward(SAVE_CHAT_ID)
        else:
            await bot.forward_message(
                chat_id=SAVE_CHAT_ID,
                from_chat_id=callback.message.chat.id,
                message_id=callback.message.message_id - 1,
            )
        await callback.answer("💾 Saqlandi!", show_alert=True)
    except Exception as e:
        logger.error(f"Saqlash xatosi: {e}")
        await callback.answer(f"❌ Saqlashda xatolik: {str(e)[:100]}", show_alert=True)

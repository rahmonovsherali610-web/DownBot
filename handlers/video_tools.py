"""Video asboblari handleri (B.1 bo'limi)."""
import os, uuid, logging, asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from states import *
from keyboards import *
from config import TEMP_DIR, BOT_USERNAME
from utils.media_processor import *
from utils.progress import ProgressTracker
from utils.uploader import send_video, send_document
from utils.cleanup import cleanup_files
from utils.helpers import parse_time_range, sanitize_filename

logger = logging.getLogger(__name__)
router = Router(name="video_tools")

# === Media Tools entry ===
@router.callback_query(F.data == "media_tools")
async def media_tools_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🛠 *Media Asboblar ombori*", reply_markup=media_tools_kb(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "mt_video")
async def video_tools_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🎬 *Video asboblari*", reply_markup=video_tools_kb(), parse_mode="Markdown")
    await callback.answer()

# Helper: video qabul qilish
async def receive_video(message: Message, state: FSMContext) -> str | None:
    if not message.video and not message.document:
        await message.answer("⚠️ Iltimos, video fayl yuboring!")
        return None
    progress = ProgressTracker(message.bot, message.chat.id, "Video qabul qilinmoqda")
    await progress.start()
    try:
        file = message.video or message.document
        fid = file.file_id
        ext = ".mp4"
        if message.document and message.document.file_name:
            ext = os.path.splitext(message.document.file_name)[1] or ".mp4"
        path = str(TEMP_DIR / f"vin_{uuid.uuid4().hex[:8]}{ext}")
        await message.bot.download(fid, destination=path)
        await progress.finish("✅ Video qabul qilindi!")
        return path
    except Exception as e:
        await progress.error(f"Video qabul qilishda xatolik: {e}")
        return None

# Helper: natijani yuborish
async def send_result_video(bot: Bot, chat_id: int, path: str, caption: str = ""):
    if not caption:
        caption = f"✅ *{BOT_USERNAME}* Bot orqali tayyorlandi."
    w, h = await get_video_resolution(path)
    dur = int(await get_media_duration(path))
    await send_video(bot, chat_id, path, caption, duration=dur, width=w, height=h)

# === 1. Kesib olish (Crop) ===
@router.callback_query(F.data == "vt_crop")
async def crop_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VideoCropStates.waiting_for_video)
    await callback.message.edit_text(
        "✂️ *Video kesib olish*\n\nMenga videoni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(VideoCropStates.waiting_for_video, F.video | F.document)
async def crop_got_video(message: Message, state: FSMContext):
    path = await receive_video(message, state)
    if not path: return
    await state.update_data(input_path=path)
    await state.set_state(VideoCropStates.waiting_for_time_range)
    await message.answer(
        "⏱ Videoni qaysi vaqtdan kesay?\n\n"
        "Format: `00:10 - 00:45`\nMisol: `00:30 - 01:30`", parse_mode="Markdown")

@router.message(VideoCropStates.waiting_for_time_range)
async def crop_process(message: Message, state: FSMContext, bot: Bot):
    times = parse_time_range(message.text)
    if not times:
        await message.answer("❌ Noto'g'ri format! Misol: `00:10 - 00:45`", parse_mode="Markdown")
        return
    data = await state.get_data()
    inp = data["input_path"]
    out = str(TEMP_DIR / f"crop_{uuid.uuid4().hex[:8]}.mp4")
    await state.set_state(VideoCropStates.processing)
    progress = ProgressTracker(bot, message.chat.id, "Video kesilmoqda")
    await progress.start()
    try:
        await crop_video(inp, out, times[0], times[1])
        await progress.finish()
        await send_result_video(bot, message.chat.id, out)
    except Exception as e:
        await progress.error(f"Kesish xatosi: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === 2. Audio ajratish ===
@router.callback_query(F.data == "vt_extract_audio")
async def extract_audio_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VideoExtractAudioStates.waiting_for_video)
    await callback.message.edit_text("🎙 *Audio ajratish*\n\nVideoni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(VideoExtractAudioStates.waiting_for_video, F.video | F.document)
async def extract_audio_got_video(message: Message, state: FSMContext):
    path = await receive_video(message, state)
    if not path: return
    await state.update_data(input_path=path)
    await state.set_state(VideoExtractAudioStates.choosing_format)
    await message.answer("🎵 Format tanlang:", reply_markup=extract_audio_format_kb())

@router.callback_query(F.data.startswith("eaf_"), VideoExtractAudioStates.choosing_format)
async def extract_audio_process(callback: CallbackQuery, state: FSMContext, bot: Bot):
    fmt = callback.data.replace("eaf_", "")
    codecs = {"mp3":"libmp3lame","m4a":"aac","ogg":"libopus","flac":"flac","wav":"pcm_s16le"}
    codec = codecs.get(fmt, "libmp3lame")
    data = await state.get_data()
    inp = data["input_path"]
    out = str(TEMP_DIR / f"exa_{uuid.uuid4().hex[:8]}.{fmt}")
    await state.set_state(VideoExtractAudioStates.processing)
    await callback.answer()
    progress = ProgressTracker(bot, callback.message.chat.id, "Audio ajratilmoqda")
    await progress.start()
    try:
        await extract_audio_from_video(inp, out, codec, fmt)
        await progress.finish()
        from utils.uploader import send_audio
        await send_audio(bot, callback.message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await callback.message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === 3. Video tezligi ===
@router.callback_query(F.data == "vt_speed")
async def speed_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VideoSpeedStates.waiting_for_video)
    await callback.message.edit_text("⏩ *Video tezligi*\n\nVideoni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(VideoSpeedStates.waiting_for_video, F.video | F.document)
async def speed_got_video(message: Message, state: FSMContext):
    path = await receive_video(message, state)
    if not path: return
    await state.update_data(input_path=path)
    await state.set_state(VideoSpeedStates.waiting_for_speed)
    await message.answer("⚡ Tezlikni yozing (0.1x - 10x):\nMisol: `0.5` yoki `2`", parse_mode="Markdown")

@router.message(VideoSpeedStates.waiting_for_speed)
async def speed_process(message: Message, state: FSMContext, bot: Bot):
    try:
        speed = float(message.text.strip().replace("x","").replace("X",""))
        if not 0.1 <= speed <= 10:
            await message.answer("❌ 0.1 dan 10 gacha bo'lishi kerak!")
            return
    except ValueError:
        await message.answer("❌ Faqat raqam yuboring! Misol: `2`", parse_mode="Markdown")
        return
    data = await state.get_data()
    inp = data["input_path"]
    out = str(TEMP_DIR / f"spd_{uuid.uuid4().hex[:8]}.mp4")
    await state.set_state(VideoSpeedStates.processing)
    progress = ProgressTracker(bot, message.chat.id, "Tezlik o'zgartirilmoqda")
    await progress.start()
    try:
        await change_video_speed(inp, out, speed)
        await progress.finish()
        await send_result_video(bot, message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === 4. Ovozsiz video ===
@router.callback_query(F.data == "vt_mute")
async def mute_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VideoMuteStates.waiting_for_video)
    await callback.message.edit_text("🔇 *Ovozsiz video*\n\nVideoni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(VideoMuteStates.waiting_for_video, F.video | F.document)
async def mute_process(message: Message, state: FSMContext, bot: Bot):
    path = await receive_video(message, state)
    if not path: return
    out = str(TEMP_DIR / f"mute_{uuid.uuid4().hex[:8]}.mp4")
    await state.set_state(VideoMuteStates.processing)
    progress = ProgressTracker(bot, message.chat.id, "Ovoz o'chirilmoqda")
    await progress.start()
    try:
        await mute_video(path, out)
        await progress.finish()
        await send_result_video(bot, message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(path, out)
        await state.clear()
        await message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === 5. Hajmni siqish ===
@router.callback_query(F.data == "vt_compress")
async def compress_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VideoCompressStates.waiting_for_video)
    await callback.message.edit_text(
        "📉 *Hajmni siqish*\n\nMen video hajmini qisqartiraman.\nMenga videoni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(VideoCompressStates.waiting_for_video, F.video | F.document)
async def compress_got_video(message: Message, state: FSMContext):
    path = await receive_video(message, state)
    if not path: return
    await state.update_data(input_path=path)
    await state.set_state(VideoCompressStates.choosing_level)
    await message.answer(
        "📦 *Hajmni boshqarish:*\n\n"
        "Siqish darajasini tanlang:", reply_markup=compress_level_kb(), parse_mode="Markdown")

@router.callback_query(F.data.startswith("crf_"), VideoCompressStates.choosing_level)
async def compress_process(callback: CallbackQuery, state: FSMContext, bot: Bot):
    crf = int(callback.data.replace("crf_", ""))
    data = await state.get_data()
    inp = data["input_path"]
    out = str(TEMP_DIR / f"cmp_{uuid.uuid4().hex[:8]}.mp4")
    await state.set_state(VideoCompressStates.processing)
    await callback.answer()
    progress = ProgressTracker(bot, callback.message.chat.id, "Siqilmoqda")
    await progress.start()
    try:
        await compress_video(inp, out, crf)
        await progress.finish()
        await send_result_video(bot, callback.message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await callback.message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === 6. Sifatni o'zgartirish ===
@router.callback_query(F.data == "vt_resolution")
async def resolution_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VideoResolutionStates.waiting_for_video)
    await callback.message.edit_text("📐 *Sifatni o'zgartirish*\n\nVideoni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(VideoResolutionStates.waiting_for_video, F.video | F.document)
async def resolution_got_video(message: Message, state: FSMContext):
    path = await receive_video(message, state)
    if not path: return
    w, h = await get_video_resolution(path)
    await state.update_data(input_path=path, current_height=h)
    await state.set_state(VideoResolutionStates.choosing_resolution)
    await message.answer(
        f"📐 Hozirgi sifat: {h}p\n\n"
        "⚠️ *Diqqat!* Resolutionni oshirish videoni tiniqlashtirmaydi, "
        "aksincha hajmini kattalashtirib sifatini xiralashtiradi!\n\n"
        "Yangi sifatni tanlang:", reply_markup=resolution_kb(h), parse_mode="Markdown")

@router.callback_query(F.data.startswith("res_"), VideoResolutionStates.choosing_resolution)
async def resolution_process(callback: CallbackQuery, state: FSMContext, bot: Bot):
    height = int(callback.data.replace("res_", ""))
    data = await state.get_data()
    inp = data["input_path"]
    out = str(TEMP_DIR / f"res_{uuid.uuid4().hex[:8]}.mp4")
    await state.set_state(VideoResolutionStates.processing)
    await callback.answer()
    progress = ProgressTracker(bot, callback.message.chat.id, "Sifat o'zgartirilmoqda")
    await progress.start()
    try:
        await change_resolution(inp, out, height)
        await progress.finish()
        await send_result_video(bot, callback.message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await callback.message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === 7. Format o'zgartirish ===
@router.callback_query(F.data == "vt_format")
async def format_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VideoFormatStates.waiting_for_video)
    await callback.message.edit_text("🔄 *Formatni o'zgartirish*\n\nVideo faylini yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(VideoFormatStates.waiting_for_video, F.video | F.document)
async def format_got_video(message: Message, state: FSMContext):
    path = await receive_video(message, state)
    if not path: return
    ext = os.path.splitext(path)[1].lstrip(".")
    await state.update_data(input_path=path, current_ext=ext)
    await state.set_state(VideoFormatStates.choosing_format)
    await message.answer(f"Hozirgi format: *{ext.upper()}*\nYangi formatni tanlang:",
                         reply_markup=video_format_kb(ext), parse_mode="Markdown")

@router.callback_query(F.data.startswith("vfmt_"), VideoFormatStates.choosing_format)
async def format_process(callback: CallbackQuery, state: FSMContext, bot: Bot):
    fmt = callback.data.replace("vfmt_", "")
    data = await state.get_data()
    inp = data["input_path"]
    out = str(TEMP_DIR / f"fmt_{uuid.uuid4().hex[:8]}.{fmt}")
    await state.set_state(VideoFormatStates.processing)
    await callback.answer()
    progress = ProgressTracker(bot, callback.message.chat.id, "Format o'zgartirilmoqda")
    await progress.start()
    try:
        await convert_video_format(inp, out, fmt)
        await progress.finish()
        if fmt == "gif":
            await bot.send_animation(callback.message.chat.id, FSInputFile(out))
        else:
            await send_result_video(bot, callback.message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await callback.message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === 8. Tomonlar nisbati ===
@router.callback_query(F.data == "vt_aspect")
async def aspect_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VideoAspectRatioStates.waiting_for_video)
    await callback.message.edit_text("📏 *Tomonlar nisbati*\n\nVideoni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(VideoAspectRatioStates.waiting_for_video, F.video | F.document)
async def aspect_got_video(message: Message, state: FSMContext):
    path = await receive_video(message, state)
    if not path: return
    await state.update_data(input_path=path)
    await state.set_state(VideoAspectRatioStates.choosing_method)
    await message.answer("Usulni tanlang:", reply_markup=aspect_method_kb())

@router.callback_query(F.data.startswith("asp_"), VideoAspectRatioStates.choosing_method)
async def aspect_choose_method(callback: CallbackQuery, state: FSMContext):
    method = "pad" if callback.data == "asp_pad" else "crop"
    await state.update_data(aspect_method=method)
    await state.set_state(VideoAspectRatioStates.choosing_ratio)
    await callback.message.edit_text("Nisbatni tanlang:", reply_markup=aspect_ratio_kb())
    await callback.answer()

@router.callback_query(F.data.startswith("ar_"), VideoAspectRatioStates.choosing_ratio)
async def aspect_process(callback: CallbackQuery, state: FSMContext, bot: Bot):
    ratio = callback.data.replace("ar_", "")
    data = await state.get_data()
    inp = data["input_path"]
    method = data.get("aspect_method", "pad")
    out = str(TEMP_DIR / f"asp_{uuid.uuid4().hex[:8]}.mp4")
    await state.set_state(VideoAspectRatioStates.processing)
    await callback.answer()
    progress = ProgressTracker(bot, callback.message.chat.id, "Nisbat o'zgartirilmoqda")
    await progress.start()
    try:
        await change_aspect_ratio(inp, out, ratio, method)
        await progress.finish()
        await send_result_video(bot, callback.message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await callback.message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === 9. Subtitrlar ===
@router.callback_query(F.data == "vt_subtitles")
async def subtitle_menu(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("📜 *Subtitrlar*", reply_markup=subtitle_menu_kb(), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "sub_extract")
async def sub_extract_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VideoSubtitleExtractStates.waiting_for_video)
    await callback.message.edit_text("📤 *Subtitrlarni olish*\n\nVideoni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(VideoSubtitleExtractStates.waiting_for_video, F.video | F.document)
async def sub_extract_process(message: Message, state: FSMContext, bot: Bot):
    path = await receive_video(message, state)
    if not path: return
    out = str(TEMP_DIR / f"sub_{uuid.uuid4().hex[:8]}.srt")
    await state.set_state(VideoSubtitleExtractStates.processing)
    progress = ProgressTracker(bot, message.chat.id, "Subtitrlar ajratilmoqda")
    await progress.start()
    try:
        result = await extract_subtitles(path, out)
        if result:
            await progress.finish()
            await send_document(bot, message.chat.id, out, "📜 Subtitrlar")
        else:
            await progress.error(
                "Kechirasiz, bu videoda subtitrlar topilmadi yoki hardcoded qilingan va ajratib bo'lmaydi.")
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(path, out)
        await state.clear()
        await message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

@router.callback_query(F.data == "sub_add")
async def sub_add_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(VideoSubtitleAddStates.waiting_for_video)
    await callback.message.edit_text("📥 *Subtitr qo'shish*\n\nAvval videoni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(VideoSubtitleAddStates.waiting_for_video, F.video | F.document)
async def sub_add_got_video(message: Message, state: FSMContext):
    path = await receive_video(message, state)
    if not path: return
    await state.update_data(input_path=path)
    await state.set_state(VideoSubtitleAddStates.waiting_for_subtitle)
    await message.answer("📄 Endi `.srt` subtitr faylini yuboring:", parse_mode="Markdown")

@router.message(VideoSubtitleAddStates.waiting_for_subtitle, F.document)
async def sub_add_process(message: Message, state: FSMContext, bot: Bot):
    doc = message.document
    if not doc.file_name or not doc.file_name.endswith((".srt", ".vtt", ".ass")):
        await message.answer("❌ Faqat .srt, .vtt yoki .ass fayl yuboring!")
        return
    sub_path = str(TEMP_DIR / f"sub_{uuid.uuid4().hex[:8]}{os.path.splitext(doc.file_name)[1]}")
    await bot.download(doc.file_id, destination=sub_path)
    data = await state.get_data()
    inp = data["input_path"]
    out = str(TEMP_DIR / f"subbed_{uuid.uuid4().hex[:8]}.mp4")
    await state.set_state(VideoSubtitleAddStates.processing)
    progress = ProgressTracker(bot, message.chat.id, "Subtitr qo'shilmoqda")
    await progress.start()
    try:
        await add_subtitles(inp, sub_path, out)
        await progress.finish()
        await send_result_video(bot, message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, sub_path, out)
        await state.clear()
        await message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === FSM uchun noto'g'ri xabar handlerlari ===
for st_class in [VideoCropStates, VideoExtractAudioStates, VideoSpeedStates,
                 VideoMuteStates, VideoCompressStates, VideoResolutionStates,
                 VideoFormatStates, VideoAspectRatioStates,
                 VideoSubtitleExtractStates, VideoSubtitleAddStates]:
    @router.message(st_class.waiting_for_video)
    async def wrong_input_video(message: Message, state: FSMContext):
        await message.answer("⚠️ Iltimos, video fayl yuboring!")

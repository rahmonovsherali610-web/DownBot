"""Audio asboblari handleri (B.2 bo'limi)."""
import os, uuid, logging, asyncio
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from states import *
from keyboards import *
from config import TEMP_DIR, BOT_USERNAME
from utils.media_processor import *
from utils.progress import ProgressTracker
from utils.uploader import send_audio, send_document
from utils.cleanup import cleanup_files
from utils.helpers import parse_time_range

logger = logging.getLogger(__name__)
router = Router(name="audio_tools")

@router.callback_query(F.data == "mt_audio")
async def audio_tools_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🎵 *Audio asboblari*", reply_markup=audio_tools_kb(), parse_mode="Markdown")
    await callback.answer()

async def receive_audio(message: Message, state: FSMContext) -> str | None:
    if not message.audio and not message.voice and not message.document:
        await message.answer("⚠️ Iltimos, audio fayl yuboring!")
        return None
    progress = ProgressTracker(message.bot, message.chat.id, "Audio qabul qilinmoqda")
    await progress.start()
    try:
        file = message.audio or message.voice or message.document
        ext = ".mp3"
        if message.audio and message.audio.file_name:
            ext = os.path.splitext(message.audio.file_name)[1] or ".mp3"
        elif message.document and message.document.file_name:
            ext = os.path.splitext(message.document.file_name)[1] or ".mp3"
        elif message.voice:
            ext = ".ogg"
        path = str(TEMP_DIR / f"ain_{uuid.uuid4().hex[:8]}{ext}")
        await message.bot.download(file.file_id, destination=path)
        await progress.finish("✅ Audio qabul qilindi!")
        return path
    except Exception as e:
        await progress.error(f"Audio qabul qilishda xatolik: {e}")
        return None

async def send_result_audio(bot, chat_id, path, caption=""):
    if not caption:
        caption = f"🎵 *{BOT_USERNAME}* Bot orqali tayyorlandi."
    dur = int(await get_media_duration(path))
    await send_audio(bot, chat_id, path, caption, duration=dur)

# === a) Metadata Editor ===
@router.callback_query(F.data == "at_metadata")
async def metadata_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AudioMetadataStates.waiting_for_audio)
    await callback.message.edit_text("🏷 *Metadata Editor*\n\nAudio yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(AudioMetadataStates.waiting_for_audio, F.audio | F.voice | F.document)
async def metadata_got_audio(message: Message, state: FSMContext):
    path = await receive_audio(message, state)
    if not path: return
    await state.update_data(input_path=path, meta_title=None, meta_artist=None, meta_cover=None)
    await state.set_state(AudioMetadataStates.choosing_field)
    await message.answer("Qaysi ma'lumotni o'zgartirmoqchisiz?", reply_markup=audio_metadata_kb())

@router.callback_query(F.data == "meta_title", AudioMetadataStates.choosing_field)
async def meta_title(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AudioMetadataStates.waiting_for_title)
    await callback.message.edit_text("📝 Yangi nomni yozing:")
    await callback.answer()

@router.message(AudioMetadataStates.waiting_for_title)
async def meta_title_set(message: Message, state: FSMContext):
    await state.update_data(meta_title=message.text)
    await state.set_state(AudioMetadataStates.choosing_field)
    await message.answer(f"✅ Nom: {message.text}\n\nYana o'zgartiring yoki Tayyor bosing:", reply_markup=audio_metadata_kb())

@router.callback_query(F.data == "meta_artist", AudioMetadataStates.choosing_field)
async def meta_artist(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AudioMetadataStates.waiting_for_artist)
    await callback.message.edit_text("🎤 Yangi artist nomini yozing:")
    await callback.answer()

@router.message(AudioMetadataStates.waiting_for_artist)
async def meta_artist_set(message: Message, state: FSMContext):
    await state.update_data(meta_artist=message.text)
    await state.set_state(AudioMetadataStates.choosing_field)
    await message.answer(f"✅ Artist: {message.text}", reply_markup=audio_metadata_kb())

@router.callback_query(F.data == "meta_cover", AudioMetadataStates.choosing_field)
async def meta_cover(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AudioMetadataStates.waiting_for_cover)
    await callback.message.edit_text("🖼 Muqova rasmini yuboring:")
    await callback.answer()

@router.message(AudioMetadataStates.waiting_for_cover, F.photo)
async def meta_cover_set(message: Message, state: FSMContext):
    photo = message.photo[-1]
    cover_path = str(TEMP_DIR / f"cover_{uuid.uuid4().hex[:8]}.jpg")
    await message.bot.download(photo.file_id, destination=cover_path)
    await state.update_data(meta_cover=cover_path)
    await state.set_state(AudioMetadataStates.choosing_field)
    await message.answer("✅ Muqova rasmi qabul qilindi!", reply_markup=audio_metadata_kb())

@router.callback_query(F.data == "meta_done", AudioMetadataStates.choosing_field)
async def meta_process(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    inp = data["input_path"]
    await state.set_state(AudioMetadataStates.processing)
    await callback.answer()
    progress = ProgressTracker(bot, callback.message.chat.id, "Metadata yangilanmoqda")
    await progress.start()
    try:
        from mutagen import File as MutagenFile
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, TIT2, TPE1, APIC
        audio_file = MutagenFile(inp, easy=True)
        if audio_file is None:
            raise ValueError("Audio fayl o'qib bo'lmadi!")
        if data.get("meta_title"):
            audio_file["title"] = data["meta_title"]
        if data.get("meta_artist"):
            audio_file["artist"] = data["meta_artist"]
        audio_file.save()
        if data.get("meta_cover"):
            try:
                mp3 = MP3(inp, ID3=ID3)
                with open(data["meta_cover"], "rb") as f:
                    mp3.tags.add(APIC(encoding=3, mime="image/jpeg", type=3, data=f.read()))
                mp3.save()
            except Exception:
                pass
        await progress.finish()
        await send_result_audio(bot, callback.message.chat.id, inp)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        cover = data.get("meta_cover")
        await cleanup_files(inp, cover)
        await state.clear()
        await callback.message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === b) Effectlar ===
@router.callback_query(F.data == "at_effects")
async def effects_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AudioEffectStates.waiting_for_audio)
    await callback.message.edit_text("🎭 *Audio Effectlar*\n\nAudio yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(AudioEffectStates.waiting_for_audio, F.audio | F.voice | F.document)
async def effects_got_audio(message: Message, state: FSMContext):
    path = await receive_audio(message, state)
    if not path: return
    await state.update_data(input_path=path)
    await state.set_state(AudioEffectStates.choosing_effect_category)
    await message.answer("Effect turini tanlang:", reply_markup=audio_effects_kb())

@router.callback_query(F.data == "eff_voice", AudioEffectStates.choosing_effect_category)
async def voice_changer_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AudioEffectStates.choosing_effect)
    await state.update_data(effect_type="voice")
    await callback.message.edit_text("🎭 Ovoz effektini tanlang:", reply_markup=voice_changer_kb())
    await callback.answer()

@router.callback_query(F.data == "eff_remix", AudioEffectStates.choosing_effect_category)
async def remix_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AudioEffectStates.choosing_effect)
    await state.update_data(effect_type="remix")
    await callback.message.edit_text("🎶 Remix turini tanlang:", reply_markup=remix_kb())
    await callback.answer()

# Voice changer effects
@router.callback_query(F.data.startswith("vc_"), AudioEffectStates.choosing_effect)
async def voice_effect_process(callback: CallbackQuery, state: FSMContext, bot: Bot):
    effect = callback.data.replace("vc_", "")
    data = await state.get_data()
    inp = data["input_path"]
    out = str(TEMP_DIR / f"vce_{uuid.uuid4().hex[:8]}.mp3")
    await state.set_state(AudioEffectStates.processing)
    await callback.answer()
    progress = ProgressTracker(bot, callback.message.chat.id, "Effect qo'llanilmoqda")
    await progress.start()
    try:
        await apply_voice_effect(inp, out, effect)
        await progress.finish()
        await send_result_audio(bot, callback.message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await callback.message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# Remix effects
@router.callback_query(F.data.startswith("rmx_"), AudioEffectStates.choosing_effect)
async def remix_process(callback: CallbackQuery, state: FSMContext, bot: Bot):
    preset = callback.data.replace("rmx_", "")
    data = await state.get_data()
    inp = data["input_path"]
    out = str(TEMP_DIR / f"rmx_{uuid.uuid4().hex[:8]}.mp3")
    await state.set_state(AudioEffectStates.processing)
    await callback.answer()
    progress = ProgressTracker(bot, callback.message.chat.id, "Remix qo'llanilmoqda")
    await progress.start()
    try:
        await apply_remix_effect(inp, out, preset)
        await progress.finish()
        await send_result_audio(bot, callback.message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await callback.message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# Direct effects (8D, Echo, Reverb, Bass, Denoise, Reverse, Stereo)
DIRECT_EFFECTS = {
    "eff_8d": ("8D Audio", apply_8d_audio),
    "eff_echo": ("Echo", apply_echo),
    "eff_reverb": ("Reverb", apply_reverb),
    "eff_bass": ("Bass Boost", apply_bass_boost),
    "eff_denoise": ("Shovqin kamaytirish", apply_noise_reduction),
    "eff_reverse": ("Teskari aylantirish", reverse_audio),
    "eff_stereo": ("Stereo", make_stereo),
}

for eff_key, (eff_name, eff_func) in DIRECT_EFFECTS.items():
    async def _make_handler(cb, st, bt, _name=eff_name, _func=eff_func):
        data = await st.get_data()
        inp = data["input_path"]
        out = str(TEMP_DIR / f"eff_{uuid.uuid4().hex[:8]}.mp3")
        await st.set_state(AudioEffectStates.processing)
        await cb.answer()
        progress = ProgressTracker(bt, cb.message.chat.id, f"{_name} qo'llanilmoqda")
        await progress.start()
        try:
            await _func(inp, out)
            await progress.finish()
            await send_result_audio(bt, cb.message.chat.id, out)
        except Exception as e:
            await progress.error(f"Xatolik: {e}")
        finally:
            await cleanup_files(inp, out)
            await st.clear()
            await cb.message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")
    router.callback_query.register(_make_handler, F.data == eff_key, AudioEffectStates.choosing_effect_category)

# === c) Birlashtirish ===
@router.callback_query(F.data == "at_merge")
async def merge_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AudioMergeStates.waiting_for_first_audio)
    await callback.message.edit_text("🔗 *Audio birlashtirish*\n\n1-audioni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(AudioMergeStates.waiting_for_first_audio, F.audio | F.voice | F.document)
async def merge_first(message: Message, state: FSMContext):
    path = await receive_audio(message, state)
    if not path: return
    await state.update_data(merge_first=path)
    await state.set_state(AudioMergeStates.waiting_for_second_audio)
    await message.answer("✅ 1-audio qabul qilindi!\n\n2-audioni yuboring:")

@router.message(AudioMergeStates.waiting_for_second_audio, F.audio | F.voice | F.document)
async def merge_second(message: Message, state: FSMContext, bot: Bot):
    path = await receive_audio(message, state)
    if not path: return
    data = await state.get_data()
    first = data["merge_first"]
    out = str(TEMP_DIR / f"mrg_{uuid.uuid4().hex[:8]}.mp3")
    await state.set_state(AudioMergeStates.processing)
    progress = ProgressTracker(bot, message.chat.id, "Birlashtirilmoqda")
    await progress.start()
    try:
        await merge_audios(first, path, out)
        await progress.finish()
        await send_result_audio(bot, message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(first, path, out)
        await state.clear()
        await message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === d) Kesish ===
@router.callback_query(F.data == "at_cut")
async def cut_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AudioCutStates.waiting_for_audio)
    await callback.message.edit_text("✂️ *Audio kesish*\n\nAudioni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(AudioCutStates.waiting_for_audio, F.audio | F.voice | F.document)
async def cut_got_audio(message: Message, state: FSMContext):
    path = await receive_audio(message, state)
    if not path: return
    await state.update_data(input_path=path)
    await state.set_state(AudioCutStates.waiting_for_time_range)
    await message.answer("⏱ Qaysi vaqtdan kesay?\nFormat: `00:10 - 00:45`", parse_mode="Markdown")

@router.message(AudioCutStates.waiting_for_time_range)
async def cut_process(message: Message, state: FSMContext, bot: Bot):
    times = parse_time_range(message.text)
    if not times:
        await message.answer("❌ Noto'g'ri format! Misol: `00:10 - 00:45`", parse_mode="Markdown")
        return
    data = await state.get_data()
    inp = data["input_path"]
    ext = os.path.splitext(inp)[1] or ".mp3"
    out = str(TEMP_DIR / f"cut_{uuid.uuid4().hex[:8]}{ext}")
    await state.set_state(AudioCutStates.processing)
    progress = ProgressTracker(bot, message.chat.id, "Audio kesilmoqda")
    await progress.start()
    try:
        await cut_audio(inp, out, times[0], times[1])
        await progress.finish()
        await send_result_audio(bot, message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === e) Audio tezligi ===
@router.callback_query(F.data == "at_speed")
async def audio_speed_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AudioSpeedStates.waiting_for_audio)
    await callback.message.edit_text("⏩ *Audio tezligi*\n\nAudioni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(AudioSpeedStates.waiting_for_audio, F.audio | F.voice | F.document)
async def audio_speed_got(message: Message, state: FSMContext):
    path = await receive_audio(message, state)
    if not path: return
    await state.update_data(input_path=path)
    await state.set_state(AudioSpeedStates.waiting_for_speed)
    await message.answer("⚡ Tezlikni yozing (0.1x - 10x):\nMisol: `0.5` yoki `2`", parse_mode="Markdown")

@router.message(AudioSpeedStates.waiting_for_speed)
async def audio_speed_process(message: Message, state: FSMContext, bot: Bot):
    try:
        speed = float(message.text.strip().replace("x",""))
        if not 0.1 <= speed <= 10:
            await message.answer("❌ 0.1 dan 10 gacha!")
            return
    except ValueError:
        await message.answer("❌ Faqat raqam!")
        return
    data = await state.get_data()
    inp = data["input_path"]
    ext = os.path.splitext(inp)[1] or ".mp3"
    out = str(TEMP_DIR / f"aspd_{uuid.uuid4().hex[:8]}{ext}")
    await state.set_state(AudioSpeedStates.processing)
    progress = ProgressTracker(bot, message.chat.id, "Tezlik o'zgartirilmoqda")
    await progress.start()
    try:
        await change_audio_speed(inp, out, speed)
        await progress.finish()
        await send_result_audio(bot, message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === f) Ovoz balandligi ===
@router.callback_query(F.data == "at_volume")
async def volume_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AudioVolumeStates.waiting_for_audio)
    await callback.message.edit_text("🔊 *Ovoz balandligi*\n\nAudioni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(AudioVolumeStates.waiting_for_audio, F.audio | F.voice | F.document)
async def volume_got_audio(message: Message, state: FSMContext):
    path = await receive_audio(message, state)
    if not path: return
    await state.update_data(input_path=path)
    await state.set_state(AudioVolumeStates.choosing_level)
    await message.answer("Ovoz darajasini tanlang:", reply_markup=audio_volume_kb())

@router.callback_query(F.data.startswith("vol_"), AudioVolumeStates.choosing_level)
async def volume_process(callback: CallbackQuery, state: FSMContext, bot: Bot):
    mode_map = {"vol_2x_up":"2x_up","vol_2x_down":"2x_down","vol_normalize":"normalize"}
    mode = mode_map.get(callback.data, "normalize")
    data = await state.get_data()
    inp = data["input_path"]
    ext = os.path.splitext(inp)[1] or ".mp3"
    out = str(TEMP_DIR / f"vol_{uuid.uuid4().hex[:8]}{ext}")
    await state.set_state(AudioVolumeStates.processing)
    await callback.answer()
    progress = ProgressTracker(bot, callback.message.chat.id, "Ovoz o'zgartirilmoqda")
    await progress.start()
    try:
        await change_audio_volume(inp, out, mode)
        await progress.finish()
        await send_result_audio(bot, callback.message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await callback.message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === g) Hajmni siqish ===
@router.callback_query(F.data == "at_compress")
async def audio_compress_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AudioCompressStates.waiting_for_audio)
    await callback.message.edit_text("📉 *Audio siqish*\n\nAudioni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(AudioCompressStates.waiting_for_audio, F.audio | F.voice | F.document)
async def audio_compress_got(message: Message, state: FSMContext):
    path = await receive_audio(message, state)
    if not path: return
    await state.update_data(input_path=path)
    await state.set_state(AudioCompressStates.choosing_bitrate)
    await message.answer("Siqish darajasini tanlang:", reply_markup=audio_compress_kb())

@router.callback_query(F.data.startswith("ac_"), AudioCompressStates.choosing_bitrate)
async def audio_compress_process(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    inp = data["input_path"]
    mono = callback.data == "ac_mono"
    bitrate_map = {"ac_256":"256k","ac_192":"192k","ac_128":"128k","ac_64":"64k","ac_mono":"128k"}
    bitrate = bitrate_map.get(callback.data, "128k")
    ext = os.path.splitext(inp)[1] or ".mp3"
    out = str(TEMP_DIR / f"acmp_{uuid.uuid4().hex[:8]}{ext}")
    await state.set_state(AudioCompressStates.processing)
    await callback.answer()
    progress = ProgressTracker(bot, callback.message.chat.id, "Siqilmoqda")
    await progress.start()
    try:
        await compress_audio(inp, out, bitrate, mono)
        await progress.finish()
        await send_result_audio(bot, callback.message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await callback.message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

# === h) Format o'zgartirish ===
@router.callback_query(F.data == "at_format")
async def audio_format_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AudioFormatStates.waiting_for_audio)
    await callback.message.edit_text("🔄 *Audio format o'zgartirish*\n\nAudioni yuboring:", parse_mode="Markdown")
    await callback.answer()

@router.message(AudioFormatStates.waiting_for_audio, F.audio | F.voice | F.document)
async def audio_format_got(message: Message, state: FSMContext):
    path = await receive_audio(message, state)
    if not path: return
    ext = os.path.splitext(path)[1].lstrip(".")
    await state.update_data(input_path=path, current_ext=ext)
    await state.set_state(AudioFormatStates.choosing_format)
    await message.answer(f"Hozirgi: *{ext.upper()}*\nYangi format:", reply_markup=audio_format_convert_kb(ext), parse_mode="Markdown")

@router.callback_query(F.data.startswith("acf_"), AudioFormatStates.choosing_format)
async def audio_format_process(callback: CallbackQuery, state: FSMContext, bot: Bot):
    fmt = callback.data.replace("acf_", "")
    codecs = {"mp3":"libmp3lame","m4a":"aac","ogg":"libopus","flac":"flac","wav":"pcm_s16le"}
    codec = codecs.get(fmt, "libmp3lame")
    data = await state.get_data()
    inp = data["input_path"]
    out = str(TEMP_DIR / f"afmt_{uuid.uuid4().hex[:8]}.{fmt}")
    await state.set_state(AudioFormatStates.processing)
    await callback.answer()
    progress = ProgressTracker(bot, callback.message.chat.id, "Format o'zgartirilmoqda")
    await progress.start()
    try:
        await convert_audio_format(inp, out, codec)
        await progress.finish()
        await send_result_audio(bot, callback.message.chat.id, out)
    except Exception as e:
        await progress.error(f"Xatolik: {e}")
    finally:
        await cleanup_files(inp, out)
        await state.clear()
        await callback.message.answer("🏠 *Asosiy menyu*", reply_markup=main_menu_kb(), parse_mode="Markdown")

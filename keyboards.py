"""Barcha inline klaviaturalar."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def back_and_cancel() -> list[list[InlineKeyboardButton]]:
    """Orqaga va Bekor qilish tugmalari."""
    return [
        [
            InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"),
        ]
    ]


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔗 Havola orqali yuklash", callback_data="download_link")],
        [InlineKeyboardButton(text="🛠 Media Asboblar ombori", callback_data="media_tools")],
        [InlineKeyboardButton(text="🤖 AI (Beta)", callback_data="ai_chat")],
        [InlineKeyboardButton(text="👤 Profil", callback_data="profile")],
        [InlineKeyboardButton(text="❓ Yordam va aloqa", callback_data="help_contact")],
        [InlineKeyboardButton(text="⚙️ Admin", callback_data="admin_panel")],
    ])


def media_info_kb(show_video=True, show_audio=True) -> InlineKeyboardMarkup:
    """Video/Audio tanlash (yuklab olish uchun)."""
    buttons = []
    if show_video:
        buttons.append([InlineKeyboardButton(text="🎬 Video", callback_data="dl_video")])
    if show_audio:
        buttons.append([InlineKeyboardButton(text="🎵 Audio", callback_data="dl_audio")])
    buttons.append([InlineKeyboardButton(text="💾 Saqlash", callback_data="dl_save")])
    buttons.extend(back_and_cancel())
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def video_quality_kb(formats_data: list[dict]) -> InlineKeyboardMarkup:
    """Video sifat tanlash tugmalari."""
    buttons = []
    for f in formats_data:
        height = f.get("height", 0)
        fps = f.get("fps", "")
        size_mb = f.get("size_mb", 0)
        label = f.get("label", f"{height}p")
        warn = " ⚠️" if size_mb >= 50 else ""
        fps_str = f"+{fps}fps" if fps and height >= 720 else ""
        text = f"📹 {label} {fps_str} (~{size_mb:.1f} MB{warn})"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"vq_{f.get('format_id', height)}"
        )])
    buttons.append([InlineKeyboardButton(text="💾 Saqlash", callback_data="dl_save")])
    buttons.extend(back_and_cancel())
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def audio_format_kb(formats_data: list[dict]) -> InlineKeyboardMarkup:
    """Audio format tanlash."""
    buttons = []
    for f in formats_data:
        fmt = f.get("ext", "mp3").upper()
        quality = f.get("quality", "")
        size_mb = f.get("size_mb", 0)
        text = f"🎵 {fmt} ({quality}) (~{size_mb:.1f} MB)"
        buttons.append([InlineKeyboardButton(
            text=text,
            callback_data=f"af_{f.get('format_id', fmt.lower())}"
        )])
    buttons.append([InlineKeyboardButton(text="💾 Saqlash", callback_data="dl_save")])
    buttons.extend(back_and_cancel())
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def media_tools_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Video", callback_data="mt_video")],
        [InlineKeyboardButton(text="🎵 Audio", callback_data="mt_audio")],
        *back_and_cancel(),
    ])


def video_tools_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✂️ Kesib olish", callback_data="vt_crop")],
        [InlineKeyboardButton(text="🎙 Audio ajratish", callback_data="vt_extract_audio")],
        [InlineKeyboardButton(text="⏩ Tezlik", callback_data="vt_speed")],
        [InlineKeyboardButton(text="🔇 Ovozsiz", callback_data="vt_mute")],
        [InlineKeyboardButton(text="📉 Hajmni siqish", callback_data="vt_compress")],
        [InlineKeyboardButton(text="📐 Sifatni o'zgartirish", callback_data="vt_resolution")],
        [InlineKeyboardButton(text="🔄 Formatni o'zgartirish", callback_data="vt_format")],
        [InlineKeyboardButton(text="📏 Tomonlar nisbati", callback_data="vt_aspect")],
        [InlineKeyboardButton(text="📜 Subtitrlar", callback_data="vt_subtitles")],
        *back_and_cancel(),
    ])


def audio_tools_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏷 Metadata Editor", callback_data="at_metadata")],
        [InlineKeyboardButton(text="🎭 Effectlar", callback_data="at_effects")],
        [InlineKeyboardButton(text="🔗 Birlashtirish", callback_data="at_merge")],
        [InlineKeyboardButton(text="✂️ Kesish", callback_data="at_cut")],
        [InlineKeyboardButton(text="⏩ Tezlik", callback_data="at_speed")],
        [InlineKeyboardButton(text="🔊 Ovoz balandligi", callback_data="at_volume")],
        [InlineKeyboardButton(text="📉 Hajmni siqish", callback_data="at_compress")],
        [InlineKeyboardButton(text="🔄 Formatni o'zgartirish", callback_data="at_format")],
        *back_and_cancel(),
    ])


def extract_audio_format_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 MP3 (Universal)", callback_data="eaf_mp3")],
        [InlineKeyboardButton(text="🎵 M4A (Yuqori sifat)", callback_data="eaf_m4a")],
        [InlineKeyboardButton(text="🎵 OGG (Telegram Voice)", callback_data="eaf_ogg")],
        [InlineKeyboardButton(text="🎵 FLAC (Professional)", callback_data="eaf_flac")],
        [InlineKeyboardButton(text="🎵 WAV (Max sifat)", callback_data="eaf_wav")],
        *back_and_cancel(),
    ])


def compress_level_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 CRF 18-23: Standart sifat", callback_data="crf_23")],
        [InlineKeyboardButton(text="📦 CRF 28: Katta siqish", callback_data="crf_28")],
        [InlineKeyboardButton(text="📦 CRF 51: Maksimal siqish", callback_data="crf_51")],
        *back_and_cancel(),
    ])


def resolution_kb(current_height: int = 0) -> InlineKeyboardMarkup:
    resolutions = [
        ("144p (Lowest)", 144), ("240p (Very low)", 240),
        ("360p (Low)", 360), ("480p (Medium)", 480),
        ("720p (HD)", 720), ("1080p (Full HD)", 1080),
    ]
    buttons = []
    for label, h in resolutions:
        marker = " ✅" if h == current_height else ""
        buttons.append([InlineKeyboardButton(
            text=f"📐 {label}{marker}", callback_data=f"res_{h}"
        )])
    buttons.extend(back_and_cancel())
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def video_format_kb(current_ext: str = "") -> InlineKeyboardMarkup:
    formats = ["MKV", "MOV", "AVI", "WebM", "GIF", "MP4"]
    buttons = []
    for f in formats:
        if f.lower() == current_ext.lower():
            continue
        buttons.append([InlineKeyboardButton(
            text=f"📁 {f}", callback_data=f"vfmt_{f.lower()}"
        )])
    buttons.extend(back_and_cancel())
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def aspect_method_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬛ Qora hoshiyali (Padding)", callback_data="asp_pad")],
        [InlineKeyboardButton(text="✂️ Kesib olish (Cropping)", callback_data="asp_crop")],
        *back_and_cancel(),
    ])


def aspect_ratio_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📺 16:9 Horizontal", callback_data="ar_16:9")],
        [InlineKeyboardButton(text="📱 9:16 Vertical", callback_data="ar_9:16")],
        [InlineKeyboardButton(text="📟 4:3 Standard", callback_data="ar_4:3")],
        [InlineKeyboardButton(text="⬜ 1:1 Square", callback_data="ar_1:1")],
        [InlineKeyboardButton(text="🎬 21:9 Cinematic", callback_data="ar_21:9")],
        *back_and_cancel(),
    ])


def subtitle_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Subtitrlarni olish", callback_data="sub_extract")],
        [InlineKeyboardButton(text="📥 Subtitr qo'shish", callback_data="sub_add")],
        *back_and_cancel(),
    ])


def audio_metadata_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Nomini o'zgartirish", callback_data="meta_title")],
        [InlineKeyboardButton(text="🎤 Artistni o'zgartirish", callback_data="meta_artist")],
        [InlineKeyboardButton(text="🖼 Muqova rasmini o'zgartirish", callback_data="meta_cover")],
        [InlineKeyboardButton(text="✅ Tayyor - Yuklab olish", callback_data="meta_done")],
        *back_and_cancel(),
    ])


def audio_effects_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎭 Ovoz o'zgartiruvchi", callback_data="eff_voice")],
        [InlineKeyboardButton(text="🎶 Remix (pitch+speed)", callback_data="eff_remix")],
        [InlineKeyboardButton(text="🎧 8D Audio Effect", callback_data="eff_8d")],
        [InlineKeyboardButton(text="🔊 Aks sado (Echo)", callback_data="eff_echo")],
        [InlineKeyboardButton(text="🏛 Reverb", callback_data="eff_reverb")],
        [InlineKeyboardButton(text="🔉 Bass Boost", callback_data="eff_bass")],
        [InlineKeyboardButton(text="🔇 Shovqin kamaytirish", callback_data="eff_denoise")],
        [InlineKeyboardButton(text="⏪ Teskari aylantirish", callback_data="eff_reverse")],
        [InlineKeyboardButton(text="🔀 Stereo", callback_data="eff_stereo")],
        *back_and_cancel(),
    ])


def voice_changer_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👩➡️👨 Female to Male", callback_data="vc_f2m")],
        [InlineKeyboardButton(text="👨➡️👩 Male to Female", callback_data="vc_m2f")],
        [InlineKeyboardButton(text="👶 Baby", callback_data="vc_baby")],
        [InlineKeyboardButton(text="🤖 Robot", callback_data="vc_robot")],
        [InlineKeyboardButton(text="🌊 Underwater", callback_data="vc_underwater")],
        [InlineKeyboardButton(text="😈 Darth Vader / Demon", callback_data="vc_demon")],
        [InlineKeyboardButton(text="🍺 Drunk", callback_data="vc_drunk")],
        [InlineKeyboardButton(text="📢 Megaphone", callback_data="vc_megaphone")],
        [InlineKeyboardButton(text="👻 Ghost", callback_data="vc_ghost")],
        [InlineKeyboardButton(text="👹 Maxluq", callback_data="vc_creature")],
        [InlineKeyboardButton(text="👽 Alien", callback_data="vc_alien")],
        [InlineKeyboardButton(text="📻 Radio", callback_data="vc_radio")],
        *back_and_cancel(),
    ])


def remix_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Deep Over Slowed", callback_data="rmx_deep_slowed")],
        [InlineKeyboardButton(text="🎵 Super Slowed", callback_data="rmx_super_slowed")],
        [InlineKeyboardButton(text="🎵 Slowed", callback_data="rmx_slowed")],
        [InlineKeyboardButton(text="🎵 Speed Up", callback_data="rmx_speedup")],
        [InlineKeyboardButton(text="🎵 Very Speed Up", callback_data="rmx_very_speedup")],
        *back_and_cancel(),
    ])


def audio_volume_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔊 2x Baland", callback_data="vol_2x_up")],
        [InlineKeyboardButton(text="🔉 2x Past", callback_data="vol_2x_down")],
        [InlineKeyboardButton(text="⚖️ Normallashtirish", callback_data="vol_normalize")],
        *back_and_cancel(),
    ])


def audio_compress_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔀 Stereo → Mono", callback_data="ac_mono")],
        [InlineKeyboardButton(text="💎 256 kbps (Studio)", callback_data="ac_256")],
        [InlineKeyboardButton(text="🎵 192 kbps (High)", callback_data="ac_192")],
        [InlineKeyboardButton(text="🎶 128 kbps (Normal)", callback_data="ac_128")],
        [InlineKeyboardButton(text="📉 64 kbps (Low)", callback_data="ac_64")],
        *back_and_cancel(),
    ])


def audio_format_convert_kb(current_ext: str = "") -> InlineKeyboardMarkup:
    formats = [
        ("MP3", "Universal", "mp3"),
        ("M4A", "Yuqori sifat", "m4a"),
        ("OGG", "Telegram Voice", "ogg"),
        ("FLAC", "Professional", "flac"),
        ("WAV", "Max sifat", "wav"),
    ]
    buttons = []
    for name, desc, ext in formats:
        if ext == current_ext.lower():
            continue
        buttons.append([InlineKeyboardButton(
            text=f"🎵 {name} ({desc})", callback_data=f"acf_{ext}"
        )])
    buttons.extend(back_and_cancel())
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def help_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚠️ Xatolik xabari", callback_data="help_error")],
        [InlineKeyboardButton(text="💻 Admin bilan aloqa", callback_data="help_admin")],
        *back_and_cancel(),
    ])


def admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🕵️ Yashirin funksiyalar", callback_data="adm_hidden")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilarni boshqarish", callback_data="adm_users")],
        [InlineKeyboardButton(text="🔧 Boshqarish", callback_data="adm_manage")],
        *back_and_cancel(),
    ])


def admin_users_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="admu_list")],
        [InlineKeyboardButton(text="🚫 Bloklash (Ban)", callback_data="admu_ban")],
        [InlineKeyboardButton(text="✅ Unban", callback_data="admu_unban")],
        [InlineKeyboardButton(text="📢 Global xabar", callback_data="admu_broadcast")],
        *back_and_cancel(),
    ])


def admin_manage_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔧 Texnik xizmatlar", callback_data="admm_tech")],
        [InlineKeyboardButton(text="🖥 Server", callback_data="admm_server")],
        *back_and_cancel(),
    ])


def admin_tech_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔒 Maintenance ON", callback_data="tech_maint_on")],
        [InlineKeyboardButton(text="🔓 Maintenance OFF", callback_data="tech_maint_off")],
        [InlineKeyboardButton(text="🔄 Restart", callback_data="tech_restart")],
        *back_and_cancel(),
    ])


def admin_server_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Logs", callback_data="srv_logs")],
        [InlineKeyboardButton(text="📊 Server holati", callback_data="srv_status")],
        [InlineKeyboardButton(text="🧹 Clear Cache", callback_data="srv_clear")],
        *back_and_cancel(),
    ])


def confirm_cancel_kb() -> InlineKeyboardMarkup:
    """Jarayonni to'xtatish tasdiqlash."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Ha, to'xtataman", callback_data="confirm_cancel")],
        [InlineKeyboardButton(text="❌ Yo'q, davom etaman", callback_data="deny_cancel")],
    ])

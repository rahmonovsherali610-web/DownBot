"""FSM (Finite State Machine) - Botning barcha holatlari."""

from aiogram.fsm.state import State, StatesGroup


class MainMenu(StatesGroup):
    menu = State()


class DownloadStates(StatesGroup):
    waiting_for_link = State()
    showing_info = State()
    choosing_video_quality = State()
    choosing_audio_format = State()
    downloading = State()
    uploading = State()


class VideoCropStates(StatesGroup):
    waiting_for_video = State()
    waiting_for_time_range = State()
    processing = State()


class VideoExtractAudioStates(StatesGroup):
    waiting_for_video = State()
    choosing_format = State()
    processing = State()


class VideoSpeedStates(StatesGroup):
    waiting_for_video = State()
    waiting_for_speed = State()
    processing = State()


class VideoMuteStates(StatesGroup):
    waiting_for_video = State()
    processing = State()


class VideoCompressStates(StatesGroup):
    waiting_for_video = State()
    choosing_level = State()
    processing = State()


class VideoResolutionStates(StatesGroup):
    waiting_for_video = State()
    choosing_resolution = State()
    processing = State()


class VideoFormatStates(StatesGroup):
    waiting_for_video = State()
    choosing_format = State()
    processing = State()


class VideoAspectRatioStates(StatesGroup):
    waiting_for_video = State()
    choosing_method = State()
    choosing_ratio = State()
    processing = State()


class VideoSubtitleExtractStates(StatesGroup):
    waiting_for_video = State()
    processing = State()


class VideoSubtitleAddStates(StatesGroup):
    waiting_for_video = State()
    waiting_for_subtitle = State()
    processing = State()


class AudioMetadataStates(StatesGroup):
    waiting_for_audio = State()
    choosing_field = State()
    waiting_for_title = State()
    waiting_for_artist = State()
    waiting_for_cover = State()
    processing = State()


class AudioEffectStates(StatesGroup):
    waiting_for_audio = State()
    choosing_effect_category = State()
    choosing_effect = State()
    processing = State()


class AudioMergeStates(StatesGroup):
    waiting_for_first_audio = State()
    waiting_for_second_audio = State()
    processing = State()


class AudioCutStates(StatesGroup):
    waiting_for_audio = State()
    waiting_for_time_range = State()
    processing = State()


class AudioSpeedStates(StatesGroup):
    waiting_for_audio = State()
    waiting_for_speed = State()
    processing = State()


class AudioVolumeStates(StatesGroup):
    waiting_for_audio = State()
    choosing_level = State()
    processing = State()


class AudioCompressStates(StatesGroup):
    waiting_for_audio = State()
    choosing_bitrate = State()
    processing = State()


class AudioFormatStates(StatesGroup):
    waiting_for_audio = State()
    choosing_format = State()
    processing = State()


class AIStates(StatesGroup):
    chatting = State()


class HelpStates(StatesGroup):
    reporting_error = State()


class AdminStates(StatesGroup):
    echo_waiting_message = State()
    ban_waiting_id = State()
    ban_waiting_reason = State()
    ban_waiting_duration = State()
    unban_waiting_id = State()
    broadcast_waiting = State()

"""Middleware: ban tekshirish, maintenance, foydalanuvchi ro'yxatdan o'tkazish, holat himoyasi."""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject
from aiogram.fsm.context import FSMContext

import config
from database import db

logger = logging.getLogger(__name__)


class RegisterUserMiddleware(BaseMiddleware):
    """Har bir xabar/callback da foydalanuvchini bazaga yozish."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user:
            await db.add_user(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
            )
        return await handler(event, data)


class BanCheckMiddleware(BaseMiddleware):
    """Ban qilingan foydalanuvchilarni bloklash."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user:
            is_banned, reason = await db.is_banned(user.id)
            if is_banned:
                reason_text = f"\n📝 Sabab: {reason}" if reason else ""
                msg = f"🚫 Siz bloklangansiz!{reason_text}"
                if isinstance(event, Message):
                    await event.answer(msg)
                elif isinstance(event, CallbackQuery):
                    await event.answer(msg, show_alert=True)
                return  # Handler ni chaqirmaymiz
        return await handler(event, data)


class MaintenanceMiddleware(BaseMiddleware):
    """Maintenance rejimida faqat adminlarga ruxsat berish."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not config.MAINTENANCE_MODE:
            return await handler(event, data)

        user = None
        if isinstance(event, Message) and event.from_user:
            user = event.from_user
        elif isinstance(event, CallbackQuery) and event.from_user:
            user = event.from_user

        if user and user.id in config.ADMIN_IDS:
            return await handler(event, data)

        msg = "🔧 Botda profilaktika ishlari olib borilmoqda. Iltimos keyinroq urinib ko'ring."
        if isinstance(event, Message):
            await event.answer(msg)
        elif isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        return


class StateGuardMiddleware(BaseMiddleware):
    """Foydalanuvchi biror jarayonda (state) turganda boshqa tugma bosganda ogohlantirish."""

    # Bu state larda himoya qo'llaniladi (processing holatlari)
    PROTECTED_STATES = {
        "VideoCropStates:processing",
        "VideoExtractAudioStates:processing",
        "VideoSpeedStates:processing",
        "VideoMuteStates:processing",
        "VideoCompressStates:processing",
        "VideoResolutionStates:processing",
        "VideoFormatStates:processing",
        "VideoAspectRatioStates:processing",
        "VideoSubtitleExtractStates:processing",
        "VideoSubtitleAddStates:processing",
        "AudioMetadataStates:processing",
        "AudioEffectStates:processing",
        "AudioMergeStates:processing",
        "AudioCutStates:processing",
        "AudioSpeedStates:processing",
        "AudioVolumeStates:processing",
        "AudioCompressStates:processing",
        "AudioFormatStates:processing",
        "DownloadStates:downloading",
        "DownloadStates:uploading",
    }

    # Bu callback lar himoyadan o'tadi (cancel/back)
    ALLOWED_CALLBACKS = {"cancel", "confirm_cancel", "deny_cancel", "back"}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        state: FSMContext = data.get("state")
        if not state:
            return await handler(event, data)

        current_state = await state.get_state()
        if not current_state or current_state not in self.PROTECTED_STATES:
            return await handler(event, data)

        # Cancel/back tugmalariga ruxsat
        if isinstance(event, CallbackQuery) and event.data in self.ALLOWED_CALLBACKS:
            return await handler(event, data)

        # Jarayon davomida boshqa tugma bosildi
        from keyboards import confirm_cancel_kb
        state_name = current_state.split(":")[1] if ":" in current_state else current_state
        process_names = {
            "processing": "jarayon",
            "downloading": "yuklab olish",
            "uploading": "yuborish",
        }
        process = process_names.get(state_name, "jarayon")
        msg = f"⚠️ Hozir {process} jarayonidasiz. To'xtatasizmi?"

        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        elif isinstance(event, Message):
            await event.answer(msg, reply_markup=confirm_cancel_kb())
        return

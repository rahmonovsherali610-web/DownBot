"""Profil handleri (E bo'limi)."""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from keyboards import main_menu_kb
from database import db

logger = logging.getLogger(__name__)
router = Router(name="profile")


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery, state: FSMContext):
    try:
        user = callback.from_user
        db_user = await db.get_user(user.id)
        created = db_user["created_at"].strftime("%Y-%m-%d") if db_user and db_user.get("created_at") else "N/A"
        text = (
            f"👤 *Profil*\n\n"
            f"📛 Foydalanuvchi: {user.full_name}\n"
            f"🆔 ID: `{user.id}`\n"
            f"👤 Username: @{user.username or 'yo`q'}\n"
            f"📅 Ro'yxatdan o'tgan: {created}\n"
        )
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back"),
             InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
        ])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Profil xatosi: {e}")
        await callback.answer(f"❌ Xatolik: {e}", show_alert=True)
    await callback.answer()

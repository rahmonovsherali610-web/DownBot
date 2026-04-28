"""Umumiy handlerlar: /start, cancel, back, confirm."""

import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from keyboards import main_menu_kb, confirm_cancel_kb
from config import ADMIN_IDS, BOT_USERNAME

logger = logging.getLogger(__name__)
router = Router(name="common")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    """Botni ishga tushirish va asosiy menyu."""
    await state.clear()
    welcome = (
        f"👋 Xush kelibsiz!\n\n"
        f"🤖 *{BOT_USERNAME}* — Professional media bot\n\n"
        f"📥 Video va Audio yuklab olish\n"
        f"🛠 Media qayta ishlash\n"
        f"🤖 AI yordamchi\n\n"
        f"Quyidagi menyudan tanlang:"
    )
    await message.answer(welcome, reply_markup=main_menu_kb(), parse_mode="Markdown")


@router.callback_query(F.data == "back")
async def callback_back(callback: CallbackQuery, state: FSMContext):
    """Orqaga - asosiy menyuga qaytish."""
    await state.clear()
    await callback.message.edit_text(
        "🏠 *Asosiy menyu*\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery, state: FSMContext):
    """Bekor qilish."""
    current = await state.get_state()
    if current and "processing" in str(current):
        await callback.message.edit_text(
            "⚠️ Hozir jarayon davom etmoqda. To'xtatasizmi?",
            reply_markup=confirm_cancel_kb(),
        )
    else:
        await state.clear()
        await callback.message.edit_text(
            "❌ Bekor qilindi.\n\n🏠 *Asosiy menyu*",
            reply_markup=main_menu_kb(),
            parse_mode="Markdown",
        )
    await callback.answer()


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Bekor qilish komandasi."""
    await state.clear()
    await message.answer(
        "❌ Bekor qilindi.\n\n🏠 *Asosiy menyu*",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown",
    )


@router.callback_query(F.data == "confirm_cancel")
async def callback_confirm_cancel(callback: CallbackQuery, state: FSMContext):
    """Jarayonni to'xtatishni tasdiqlash."""
    await state.clear()
    await callback.message.edit_text(
        "✅ Jarayon to'xtatildi.\n\n🏠 *Asosiy menyu*",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "deny_cancel")
async def callback_deny_cancel(callback: CallbackQuery):
    """Jarayonni davom ettirish."""
    await callback.answer("✅ Jarayon davom etmoqda...", show_alert=False)
    try:
        await callback.message.delete()
    except Exception:
        pass


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Asosiy menyuga qaytish."""
    await state.clear()
    await callback.message.edit_text(
        "🏠 *Asosiy menyu*\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown",
    )
    await callback.answer()

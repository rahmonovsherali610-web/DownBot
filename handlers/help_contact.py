"""Yordam va aloqa handleri (F bo'limi)."""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states import HelpStates
from keyboards import help_kb, main_menu_kb
from config import ADMIN_USERNAME
from database import db

logger = logging.getLogger(__name__)
router = Router(name="help")


@router.callback_query(F.data == "help_contact")
async def help_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❓ *Yordam va aloqa*\n\nQuyidagilardan birini tanlang:",
        reply_markup=help_kb(), parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "help_error")
async def report_error(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HelpStates.reporting_error)
    await callback.message.edit_text(
        "⚠️ *Xatolik xabari*\n\n"
        "Bot funksiyasidagi xatolikni batafsil yozing:\n"
        "• Qaysi bo'limda xatolik?\n• Nima qildingiz?\n• Qanday xatolik chiqdi?",
        parse_mode="Markdown",
    )
    await callback.answer()


@router.message(HelpStates.reporting_error)
async def process_error_report(message: Message, state: FSMContext):
    try:
        await db.add_error_report(message.from_user.id, message.text)
        await message.answer(
            "✅ Xatolik haqidagi xabaringiz qabul qilindi! Rahmat.\n\n🏠 *Asosiy menyu*",
            reply_markup=main_menu_kb(), parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Xatolik hisoboti: {e}")
        await message.answer(f"❌ Xatolik: {e}")
    await state.clear()


@router.callback_query(F.data == "help_admin")
async def contact_admin(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        f"💻 *Admin bilan aloqa*\n\n"
        f"Shaxsiy savollar va takliflar uchun:\n"
        f"👤 {ADMIN_USERNAME}",
        reply_markup=main_menu_kb(), parse_mode="Markdown",
    )
    await callback.answer()

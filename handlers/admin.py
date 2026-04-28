"""Admin panel handleri (G bo'limi)."""
import os
import sys
import logging
import psutil
import asyncio
from datetime import datetime, timedelta, timezone

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext

import config
from states import AdminStates
from keyboards import (admin_kb, admin_users_kb, admin_manage_kb,
                       admin_tech_kb, admin_server_kb, main_menu_kb)
from database import db
from utils.cleanup import cleanup_temp_dir, get_temp_dir_size

logger = logging.getLogger(__name__)
router = Router(name="admin")


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("🚫 Sizda ruxsat yo'q!", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        "⚙️ *Admin Panel*", reply_markup=admin_kb(), parse_mode="Markdown")
    await callback.answer()


# === Yashirin funksiyalar ===
@router.callback_query(F.data == "adm_hidden")
async def hidden_functions(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.echo_waiting_message)
    await callback.message.edit_text(
        "🕵️ *Yashirin funksiyalar*\n\n"
        "Echo xabar yuborish:\n"
        "`/echo [tg_id] [matn]`\n\n"
        "Xabarni yozing yoki /cancel bosing.",
        parse_mode="Markdown")
    await callback.answer()


@router.message(AdminStates.echo_waiting_message)
async def process_echo(message: Message, state: FSMContext, bot: Bot):
    try:
        text = message.text.strip()
        if text.startswith("/echo"):
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                await message.answer("❌ Format: `/echo [id] [matn]`", parse_mode="Markdown")
                return
            target = int(parts[1]) if parts[1].isdigit() else parts[1]
            msg_text = parts[2]
            await bot.send_message(target, msg_text)
            await message.answer("✅ Xabar yuborildi!")
        else:
            await message.answer("❌ `/echo` bilan boshlang", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
    await state.clear()


# === Foydalanuvchilar boshqarish ===
@router.callback_query(F.data == "adm_users")
async def users_management(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text(
        "👥 *Foydalanuvchilarni boshqarish*",
        reply_markup=admin_users_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admu_list")
async def users_list(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    users = await db.get_all_users()
    count = len(users)
    text = f"👥 *Foydalanuvchilar: {count} ta*\n\n"
    for i, u in enumerate(users[:50], 1):
        username = f"@{u['username']}" if u.get('username') else "N/A"
        ban = " 🚫" if u.get('is_banned') else ""
        text += f"{i}. {username} : `{u['user_id']}`{ban}\n"
    if count > 50:
        text += f"\n... va yana {count - 50} ta"
    await callback.message.edit_text(text, reply_markup=admin_users_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admu_ban")
async def ban_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.ban_waiting_id)
    await callback.message.edit_text(
        "🚫 *Ban qilish*\n\nFoydalanuvchi ID sini yuboring:",
        parse_mode="Markdown")
    await callback.answer()


@router.message(AdminStates.ban_waiting_id)
async def ban_get_id(message: Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
        await state.update_data(ban_target=uid)
        await state.set_state(AdminStates.ban_waiting_reason)
        await message.answer("📝 Ban sababini yozing:")
    except ValueError:
        await message.answer("❌ Faqat raqam (ID) yuboring!")


@router.message(AdminStates.ban_waiting_reason)
async def ban_get_reason(message: Message, state: FSMContext):
    await state.update_data(ban_reason=message.text)
    await state.set_state(AdminStates.ban_waiting_duration)
    await message.answer("⏰ Ban muddati (soatlarda, 0 = doimiy):")


@router.message(AdminStates.ban_waiting_duration)
async def ban_execute(message: Message, state: FSMContext, bot: Bot):
    try:
        hours = int(message.text.strip())
        data = await state.get_data()
        uid = data["ban_target"]
        reason = data["ban_reason"]
        until = None
        if hours > 0:
            until = datetime.now(timezone.utc) + timedelta(hours=hours)
        await db.ban_user(uid, reason, until)
        duration_text = f"{hours} soat" if hours > 0 else "Doimiy"
        await message.answer(f"✅ Foydalanuvchi `{uid}` bloklandi!\nMuddat: {duration_text}",
                             reply_markup=admin_kb(), parse_mode="Markdown")
        try:
            ban_msg = f"🚫 Siz bloklangansiz!\n📝 Sabab: {reason}\n⏰ Muddat: {duration_text}"
            await bot.send_message(uid, ban_msg)
        except Exception:
            pass
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
    await state.clear()


@router.callback_query(F.data == "admu_unban")
async def unban_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.unban_waiting_id)
    await callback.message.edit_text("✅ *Unban*\n\nFoydalanuvchi ID yuboring:", parse_mode="Markdown")
    await callback.answer()


@router.message(AdminStates.unban_waiting_id)
async def unban_execute(message: Message, state: FSMContext, bot: Bot):
    try:
        uid = int(message.text.strip())
        await db.unban_user(uid)
        await message.answer(f"✅ `{uid}` blokdan chiqarildi!", reply_markup=admin_kb(), parse_mode="Markdown")
        try:
            await bot.send_message(uid, "🎉 Siz blokdan chiqarildingiz! Botdan qayta foydalanishingiz mumkin.")
        except Exception:
            pass
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
    await state.clear()


@router.callback_query(F.data == "admu_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.broadcast_waiting)
    await callback.message.edit_text("📢 *Global xabar*\n\nXabar matnini yozing:", parse_mode="Markdown")
    await callback.answer()


@router.message(AdminStates.broadcast_waiting)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
    user_ids = await db.get_active_user_ids()
    sent, failed = 0, 0
    status_msg = await message.answer(f"📤 Yuborilmoqda... 0/{len(user_ids)}")
    for uid in user_ids:
        try:
            await bot.send_message(uid, message.text)
            sent += 1
        except Exception:
            failed += 1
        if (sent + failed) % 10 == 0:
            try:
                await status_msg.edit_text(f"📤 Yuborilmoqda... {sent+failed}/{len(user_ids)}")
            except Exception:
                pass
        await asyncio.sleep(0.05)  # Flood himoya
    try:
        await status_msg.edit_text(f"✅ Yuborildi: {sent} | ❌ Xato: {failed}")
    except Exception:
        pass
    await state.clear()


# === Boshqarish ===
@router.callback_query(F.data == "adm_manage")
async def manage_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🔧 *Boshqarish*", reply_markup=admin_manage_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "admm_tech")
async def tech_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    status = "🔒 ON" if config.MAINTENANCE_MODE else "🔓 OFF"
    await callback.message.edit_text(
        f"🔧 *Texnik xizmatlar*\n\nHolat: {status}",
        reply_markup=admin_tech_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "tech_maint_on")
async def maintenance_on(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    config.MAINTENANCE_MODE = True
    await callback.answer("🔒 Maintenance rejimi yoqildi!", show_alert=True)


@router.callback_query(F.data == "tech_maint_off")
async def maintenance_off(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    config.MAINTENANCE_MODE = False
    await callback.answer("🔓 Maintenance rejimi o'chirildi!", show_alert=True)


@router.callback_query(F.data == "tech_restart")
async def restart_bot(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.answer("🔄 Bot qayta ishga tushirilmoqda...", show_alert=True)
    os.execv(sys.executable, [sys.executable] + sys.argv)


@router.callback_query(F.data == "admm_server")
async def server_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🖥 *Server*", reply_markup=admin_server_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "srv_status")
async def server_status(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    temp_size = get_temp_dir_size()

    def indicator(val):
        if val < 50: return "🟢"
        elif val < 80: return "🟡"
        return "🔴"

    text = (
        f"🖥 *Server holati*\n\n"
        f"{indicator(cpu)} CPU: {cpu}%\n"
        f"{indicator(ram.percent)} RAM: {ram.percent}% ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB)\n"
        f"{indicator(disk.percent)} Disk: {disk.percent}% ({disk.free // (1024**3)}GB bo'sh)\n"
        f"📁 Temp: {temp_size:.1f} MB\n"
    )
    await callback.message.edit_text(text, reply_markup=admin_server_kb(), parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "srv_logs")
async def server_logs(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return
    log_file = "bot.log"
    if os.path.exists(log_file):
        await bot.send_document(callback.message.chat.id, FSInputFile(log_file), caption="📋 Oxirgi loglar")
    else:
        await callback.answer("📋 Log fayl topilmadi", show_alert=True)
    await callback.answer()


@router.callback_query(F.data == "srv_clear")
async def clear_cache(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    count = await cleanup_temp_dir()
    await callback.answer(f"🧹 {count} ta fayl o'chirildi!", show_alert=True)

"""AI handleri - DeepSeek API (D bo'limi)."""
import logging
import aiohttp
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from states import AIStates
from keyboards import main_menu_kb
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL

logger = logging.getLogger(__name__)
router = Router(name="ai")


@router.callback_query(F.data == "ai_chat")
async def start_ai(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AIStates.chatting)
    await state.update_data(ai_history=[])
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Tarixni tozalash", callback_data="ai_clear")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back"),
         InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel")]
    ])
    await callback.message.edit_text(
        "🤖 *AI Yordamchi (Beta)*\n\n"
        "Savolingizni yozing. Men aniq, to'liq va kengroq javob beraman.\n"
        "Chiqish uchun /cancel bosing.",
        reply_markup=kb, parse_mode="Markdown",
    )
    await callback.answer()


@router.callback_query(F.data == "ai_clear", AIStates.chatting)
async def clear_ai_history(callback: CallbackQuery, state: FSMContext):
    await state.update_data(ai_history=[])
    await callback.answer("🗑 Tarix tozalandi!", show_alert=True)


@router.message(AIStates.chatting)
async def process_ai_message(message: Message, state: FSMContext):
    if not DEEPSEEK_API_KEY:
        await message.answer("❌ AI API kaliti sozlanmagan!")
        return

    thinking_msg = await message.answer("🤔 O'ylayapman...")
    data = await state.get_data()
    history = data.get("ai_history", [])
    history.append({"role": "user", "content": message.text})

    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": (
                    "Sen professional yordamchisan. Har qanday savolga aniq, to'liq, "
                    "tasdiqlangan va kengroq yoritilgan javob ber. O'zbek tilida javob ber."
                )},
                *history[-10:]
            ],
            "temperature": 0.7,
            "max_tokens": 4096,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{DEEPSEEK_BASE_URL}/chat/completions",
                headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status != 200:
                    err = await resp.text()
                    raise ValueError(f"API xatosi ({resp.status}): {err[:200]}")
                result = await resp.json()

        answer = result["choices"][0]["message"]["content"]
        history.append({"role": "assistant", "content": answer})
        await state.update_data(ai_history=history)

        try:
            await thinking_msg.delete()
        except Exception:
            pass

        # Uzun javoblarni bo'lish
        if len(answer) > 4000:
            for i in range(0, len(answer), 4000):
                await message.answer(answer[i:i+4000])
        else:
            await message.answer(answer)

    except Exception as e:
        logger.error(f"AI xatosi: {e}")
        try:
            await thinking_msg.edit_text(f"❌ AI xatosi: {str(e)[:300]}")
        except Exception:
            await message.answer(f"❌ AI xatosi: {str(e)[:300]}")

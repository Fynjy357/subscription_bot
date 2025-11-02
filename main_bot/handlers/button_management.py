"""
main_bot/handlers/button_management.py
Обработчики управления кнопками бота
"""

import logging
import sys
import os
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

# Добавляем корневую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database import get_bot_by_id, update_bot_button_url, remove_bot_button_url
from main_bot.states import EditBotButton
from main_bot.keyboards import get_main_user_keyboard

logger = logging.getLogger(__name__)

async def setup_button_management_handlers(router: Router):
    """Настройка обработчиков управления кнопками"""
    
    @router.callback_query(F.data.startswith("edit_button_"))
    async def edit_bot_button_callback(callback: CallbackQuery, state: FSMContext):
        """Редактирование кнопки бота"""
        bot_id = int(callback.data.replace("edit_button_", ""))
        
        # Проверяем права доступа
        bot = await get_bot_by_id(bot_id, callback.from_user.id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return
        
        await state.update_data(edit_bot_id=bot_id)
        
        # Получаем текущую кнопку
        current_button = bot[6] if len(bot) > 6 else ""  # button_url
        
        await callback.message.answer(
            "🔘 Отправьте текст или ссылку для кнопки:\n\n"
            "• Для URL-кнопки отправьте полную ссылку (https://example.com)\n"
            "• Для текстовой кнопки отправьте любой текст\n"
            "• Чтобы удалить кнопку, отправьте \"-\"\n\n"
            f"Текущая кнопка: {current_button if current_button else 'Не установлена'}"
        )
        
        await state.set_state(EditBotButton.waiting_for_button)
        await callback.answer()

    @router.message(EditBotButton.waiting_for_button)
    async def process_edit_button(message: Message, state: FSMContext):
        """Обработка новой кнопки для бота"""
        new_button = message.text.strip()
        data = await state.get_data()
        bot_id = data.get('edit_bot_id')
        
        try:
            # Если пользователь хочет удалить кнопку
            if new_button.lower() == '-':
                await remove_bot_button_url(bot_id, message.from_user.id)
                response_text = "✅ Кнопка бота удалена!"
            else:
                await update_bot_button_url(bot_id, message.from_user.id, new_button)
                response_text = f"✅ Кнопка бота обновлена!\n\n🔘 Новая кнопка: {new_button}"
            
            await message.answer(
                response_text,
                reply_markup=await get_main_user_keyboard(message.from_user.id)
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка при обновлении кнопки: {e}")
            await message.answer(
                "❌ Произошла ошибка при обновлении кнопки.",
                reply_markup=await get_main_user_keyboard(message.from_user.id)
            )
        
        await state.clear()

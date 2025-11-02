"""
main_bot/handlers/message_management.py
Обработчики управления сообщениями бота
"""

import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import get_bot_by_id, update_bot_message, get_bot_message
from ..states import EditBotMessage
from ..keyboards import get_main_user_keyboard

async def setup_message_management_handlers(router: Router):
    """Настройка обработчиков управления сообщениями"""
    
    @router.callback_query(F.data.startswith("edit_message_"))
    async def edit_bot_message_callback(callback: CallbackQuery, state: FSMContext):
        """Редактирование сообщения бота"""
        bot_id = int(callback.data.replace("edit_message_", ""))
        
        # Проверяем права доступа
        bot = await get_bot_by_id(bot_id, callback.from_user.id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return
        
        await state.update_data(edit_bot_id=bot_id)
        
        # Получаем текущее сообщение
        current_message = await get_bot_message(bot_id)
        
        await callback.message.answer(
            "📝 Отправьте новое сообщение для бота в формате HTML:\n\n"
            "Доступные теги:\n"
            "• <b>жирный текст</b>\n"
            "• <i>курсив</i>\n"
            "• <u>подчеркнутый</u>\n"
            "• <s>зачеркнутый</s>\n"
            "• <a href='url'>ссылка</a>\n"
            "• <code>моноширинный</code>\n"
            "• <pre>блок кода</pre>\n\n"
            f"Текущее сообщение: {current_message if current_message else 'Не установлено'}\n\n"
            "Чтобы удалить сообщение, отправьте \"-\""
        )
        
        await state.set_state(EditBotMessage.waiting_for_message)
        await callback.answer()

    @router.message(EditBotMessage.waiting_for_message)
    async def process_edit_message(message: Message, state: FSMContext):
        """Обработка нового сообщения для бота"""
        new_message = message.text.strip()
        data = await state.get_data()
        bot_id = data.get('edit_bot_id')
        
        # Если пользователь хочет удалить сообщение
        if new_message.lower() == '-':
            new_message = ""
        
        try:
            await update_bot_message(bot_id, message.from_user.id, new_message)
            
            response_text = "✅ Сообщение бота обновлено!"
            if new_message:
                response_text += f"\n\n📝 Новое сообщение:\n{new_message}"
            else:
                response_text += "\n\n📝 Сообщение удалено."
            
            await message.answer(
                response_text,
                reply_markup=await get_main_user_keyboard(message.from_user.id),
                parse_mode="HTML" if new_message else None
            )
            
        except Exception as e:
            logging.error(f"❌ Ошибка при обновлении сообщения: {e}")
            await message.answer(
                "❌ Произошла ошибка при обновлении сообщения.",
                reply_markup=await get_main_user_keyboard(message.from_user.id)
            )
        
        await state.clear()

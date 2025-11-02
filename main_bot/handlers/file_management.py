"""
main_bot/handlers/file_management.py
Обработчики управления файлами бота
"""

import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import get_bot_by_id, update_bot_file, remove_bot_file
from ..states import EditBotFile
from ..keyboards import get_main_user_keyboard

async def setup_file_management_handlers(router: Router):
    """Настройка обработчиков управления файлами"""
    
    @router.callback_query(F.data.startswith("edit_file_"))
    async def edit_bot_file_callback(callback: CallbackQuery, state: FSMContext):
        """Редактирование файла бота"""
        bot_id = int(callback.data.replace("edit_file_", ""))
        
        # Проверяем права доступа
        bot = await get_bot_by_id(bot_id, callback.from_user.id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return
        
        await state.update_data(edit_bot_id=bot_id)
        
        # Получаем текущий файл
        current_file_type = bot[8] if len(bot) > 8 else ""  # file_type
        has_file = bool(current_file_type)
        
        await callback.message.answer(
            "📎 Отправьте файл для бота (фото, видео или документ до 25 МБ):\n\n"
            "• Поддерживаемые типы: фото, видео, документы\n"
            "• Максимальный размер: 25 МБ\n"
            "• Чтобы удалить файл, отправьте \"-\"\n\n"
            f"Текущий файл: {'Есть (' + current_file_type + ')' if has_file else 'Не установлен'}"
        )
        
        await state.set_state(EditBotFile.waiting_for_file)
        await callback.answer()

    @router.message(EditBotFile.waiting_for_file)
    async def process_edit_file(message: Message, state: FSMContext):
        """Обработка нового файла для бота"""
        data = await state.get_data()
        bot_id = data.get('edit_bot_id')
        
        try:
            # Если пользователь хочет удалить файл
            if message.text and message.text.strip().lower() == '-':
                await remove_bot_file(bot_id, message.from_user.id)
                response_text = "✅ Файл бота удален!"
            elif message.photo:
                # Фото
                file_id = message.photo[-1].file_id
                await update_bot_file(bot_id, message.from_user.id, file_id, 'photo')
                response_text = "✅ Фото бота обновлено!"
            elif message.video:
                # Видео
                file_id = message.video.file_id
                await update_bot_file(bot_id, message.from_user.id, file_id, 'video')
                response_text = "✅ Видео бота обновлено!"
            elif message.document:
                # Документ
                file_id = message.document.file_id
                await update_bot_file(bot_id, message.from_user.id, file_id, 'document')
                response_text = "✅ Документ бота обновлено!"
            else:
                await message.answer(
                    "❌ Пожалуйста, отправьте фото, видео или документ (до 25 МБ), либо \"-\" для удаления файла.",
                    reply_markup=await get_main_user_keyboard(message.from_user.id)
                )
                return
            
            await message.answer(
                response_text,
                reply_markup=await get_main_user_keyboard(message.from_user.id)
            )
            
        except Exception as e:
            logging.error(f"❌ Ошибка при обновлении файла: {e}")
            await message.answer(
                "❌ Произошла ошибка при обновлении файла.",
                reply_markup=await get_main_user_keyboard(message.from_user.id)
            )
        
        await state.clear()

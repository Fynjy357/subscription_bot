"""
main_bot/handlers/image_management.py
Обработчики управления изображениями бота (новая версия с сохранением на сервер)
"""

import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import get_bot_by_id, update_bot_image, remove_bot_image
from main_bot.file_utils import save_bot_image_from_main_bot, cleanup_old_images
from ..states import AttachImage
from ..keyboards import get_back_to_bot_keyboard

async def setup_image_management_handlers(router: Router):
    """Настройка обработчиков управления изображениями"""
    
    @router.callback_query(F.data.startswith("attach_image_"))
    async def attach_image_callback(callback: CallbackQuery, state: FSMContext):
        """Прикрепление изображения к боту"""
        bot_id = int(callback.data.replace("attach_image_", ""))
        
        # Проверяем права доступа
        bot = await get_bot_by_id(bot_id, callback.from_user.id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return
        
        await state.update_data(attach_bot_id=bot_id)
        
        # Получаем текущее изображение
        current_filename = bot[9] if len(bot) > 9 else ""  # image_filename (10-й элемент)
        has_image = bool(current_filename)
        
        await callback.message.answer(
            "🖼️ <b>Прикрепить изображение для бота</b>\n\n"
            "Отправьте изображение как фото или документ:\n\n"
            "• Изображение будет отображаться в основном сообщении бота\n"
            "• Поддерживаются форматы: JPG, PNG, GIF\n"
            "• Максимальный размер: 10 МБ\n\n"
            "Чтобы удалить изображение, отправьте \"-\"\n\n"
            f"Текущее изображение: {'🖼️ Установлено' if has_image else '❌ Не установлено'}",
            reply_markup=get_back_to_bot_keyboard(bot_id),
            parse_mode="HTML"
        )
        
        await state.set_state(AttachImage.waiting_for_image)
        await callback.answer()

    @router.message(AttachImage.waiting_for_image)
    async def process_attach_image(message: Message, state: FSMContext):
        """Обработка нового изображения для бота"""
        data = await state.get_data()
        bot_id = data.get('attach_bot_id')
        
        try:
            # Если пользователь хочет удалить изображение
            if message.text and message.text.strip().lower() == '-':
                await remove_bot_image(bot_id, message.from_user.id)
                response_text = "✅ Изображение бота удалено!"
            elif message.photo or message.document:
                # Сохраняем изображение на сервер
                filename = await save_bot_image_from_main_bot(bot_id, message)
                
                # Удаляем старые изображения
                cleanup_old_images(bot_id, filename)
                
                # Сохраняем имя файла в базу
                await update_bot_image(bot_id, message.from_user.id, filename)
                
                response_text = "✅ Изображение бота успешно прикреплено!\n\nТеперь оно будет отображаться в основном сообщении бота."
            else:
                await message.answer(
                    "❌ Пожалуйста, отправьте изображение (фото или документ), либо \"-\" для удаления изображения.",
                    reply_markup=get_back_to_bot_keyboard(bot_id)
                )
                return
            
            await message.answer(
                response_text,
                reply_markup=get_back_to_bot_keyboard(bot_id)
            )
            
        except Exception as e:
            logging.error(f"❌ Ошибка при прикреплении изображения: {e}")
            await message.answer(
                "❌ Произошла ошибка при прикреплении изображения.",
                reply_markup=get_back_to_bot_keyboard(bot_id)
            )
        
        await state.clear()

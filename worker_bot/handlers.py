"""
worker_bot/handlers.py
Обработчики команд и callback'ов для рабочих ботов
"""

import logging
import os
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, InputMediaPhoto, FSInputFile
from aiogram.filters import CommandStart
from .reminder_manager import start_reminders, stop_reminders


from .core import (
    check_user_subscriptions,
    get_bot_data_for_worker,
    format_subscription_message,
    get_image_caption,
    format_materials_message,
    send_subscription_success_message
)
from .keyboards import create_subscription_keyboard, main_menu_kb
from .media_utils import send_media_with_message, edit_media_message

def setup_handlers(router: Router, bot_id: int):
    """
    Настраивает обработчики для роутера
    
    Args:
        router: Роутер aiogram
        bot_id: ID бота для которого настраиваются обработчики
    """
    
    @router.message(CommandStart())
    async def cmd_start_worker(message: Message):
        """Обработчик команды /start для рабочего бота"""
        user_id = message.from_user.id
        
        # Проверяем подписки пользователя
        not_subscribed_channels, channels_with_names = await check_user_subscriptions(user_id, bot_id)
        
        logging.info(f"🔍 Проверка подписок для пользователя {user_id}")
        logging.info(f"📋 Все каналы: {channels_with_names}")
        logging.info(f"❌ Не подписан на: {not_subscribed_channels}")
        
        if not channels_with_names:
            await message.answer("❌ Бот не настроен. Обратитесь к администратору.")
            return
        
        # Получаем данные бота
        bot_data = await get_bot_data_for_worker(bot_id)
        if not bot_data:
            await message.answer("❌ Бот не найден в базе данных.")
            return
        
        # Если пользователь подписан на все проверяемые каналы
        if not not_subscribed_channels:
            # Используем новую функцию для отправки сообщения об успешной подписке
            await send_subscription_success_message(message, bot_data, user_id)
            return
        
        # Если пользователь НЕ подписан на все каналы, показываем кнопки для подписки
        bot_custom_message = bot_data[5] if bot_data[5] else ""  # message
        image_filename = bot_data[9] if bot_data[9] else ""  # image_filename
        
        # Формируем подпись для изображения
        caption = get_image_caption(bot_custom_message, channels_with_names)
        keyboard = create_subscription_keyboard(not_subscribed_channels, channels_with_names)
        
        logging.info(f"⌨️ Создана клавиатура с {len(not_subscribed_channels)} кнопками")
        
        # ОТПРАВЛЯЕМ ИЗОБРАЖЕНИЕ С ПОДПИСЬЮ (если есть изображение)
        sent_message = None
        if image_filename:
            try:
                # Получаем путь к изображению
                from main_bot.file_utils import get_bot_image_path
                image_path = get_bot_image_path(bot_id, image_filename)
                
                if os.path.exists(image_path):
                    # Используем FSInputFile для отправки локального файла
                    photo = FSInputFile(image_path)
                    sent_message = await message.answer_photo(
                        photo=photo,
                        caption=caption,
                        reply_markup=keyboard,
                        parse_mode="HTML" if bot_custom_message else None
                    )
                    logging.info(f"🖼️ Отправлено изображение для бота {bot_id}")
                else:
                    logging.warning(f"⚠️ Файл изображения не найден: {image_path}")
                    # Отправляем текстовое сообщение если файл не найден
                    full_message = format_subscription_message(bot_custom_message, channels_with_names)
                    sent_message = await message.answer(
                        full_message,
                        reply_markup=keyboard,
                        disable_web_page_preview=True,
                        parse_mode="HTML" if bot_custom_message else None
                    )
            except Exception as e:
                logging.error(f"❌ Ошибка отправки изображения: {e}")
                # Если не удалось отправить изображение, отправляем текстовое сообщение
                full_message = format_subscription_message(bot_custom_message, channels_with_names)
                sent_message = await message.answer(
                    full_message,
                    reply_markup=keyboard,
                    disable_web_page_preview=True,
                    parse_mode="HTML" if bot_custom_message else None
                )
        else:
            # Если изображения нет, отправляем текстовое сообщение
            full_message = format_subscription_message(bot_custom_message, channels_with_names)
            sent_message = await message.answer(
                full_message,
                reply_markup=keyboard,
                disable_web_page_preview=True,
                parse_mode="HTML" if bot_custom_message else None
            )
        
        # ЗАПУСКАЕМ НАПОМИНАНИЯ (после отправки сообщения с кнопками)
        if not_subscribed_channels and sent_message:
            from .reminder_manager import start_reminders
            try:
                await start_reminders(bot_id, user_id, sent_message.message_id)
                logging.info(f"🔔 Запущены напоминания для пользователя {user_id}")
            except Exception as e:
                logging.error(f"❌ Ошибка запуска напоминаний: {e}")

    @router.callback_query(F.data == "check_subs")
    async def check_subs_callback(callback: CallbackQuery):
        """Обработчик кнопки 'Проверить подписки'"""
        user_id = callback.from_user.id
        
        try:
            # Отвечаем на callback сразу
            await callback.answer("🔍 Проверяем подписки...", show_alert=False)
            
            # Проверяем подписки пользователя
            not_subscribed_channels, channels_with_names = await check_user_subscriptions(user_id, bot_id)
            
            logging.info(f"🔍 Проверка подписок для пользователя {user_id}")
            logging.info(f"❌ Не подписан на: {not_subscribed_channels}")
            
            if not channels_with_names:
                await callback.message.answer("❌ Бот не настроен. Обратитесь к администратору.")
                return
            
            # Получаем данные бота
            bot_data = await get_bot_data_for_worker(bot_id)
            if not bot_data:
                await callback.message.answer("❌ Бот не найден в базе данных.")
                return
            
            # Если пользователь подписан на все каналы
            if not not_subscribed_channels:
                # Останавливаем напоминания
                await stop_reminders(bot_id, user_id)
                
                # Отправляем сообщение об успешной подписке
                await send_subscription_success_message(callback.message, bot_data, user_id)
                
                # Пытаемся удалить старое сообщение с кнопками
                try:
                    await callback.message.delete()
                except TelegramBadRequest as e:
                    logging.warning(f"⚠️ Не удалось удалить сообщение: {e}")
                
                return
            
            # Если пользователь НЕ подписан на все каналы
            bot_custom_message = bot_data[5] if bot_data[5] else ""  # message
            image_filename = bot_data[9] if bot_data[9] else ""  # image_filename
            
            # Формируем сообщение
            caption = get_image_caption(bot_custom_message, channels_with_names)
            keyboard = create_subscription_keyboard(not_subscribed_channels, channels_with_names)
            
            # Обновляем сообщение с новыми данными
            try:
                # Если есть изображение, обновляем медиа
                if image_filename:
                    from main_bot.file_utils import get_bot_image_path
                    import os
                    
                    image_path = get_bot_image_path(bot_id, image_filename)
                    if os.path.exists(image_path):
                        from aiogram.types import InputMediaPhoto, FSInputFile
                        
                        photo = FSInputFile(image_path)
                        media = InputMediaPhoto(
                            media=photo,
                            caption=caption,
                            parse_mode="HTML" if bot_custom_message else None
                        )
                        
                        await callback.message.edit_media(
                            media=media,
                            reply_markup=keyboard
                        )
                    else:
                        await callback.message.edit_text(
                            caption,
                            reply_markup=keyboard,
                            disable_web_page_preview=True,
                            parse_mode="HTML" if bot_custom_message else None
                        )
                else:
                    await callback.message.edit_text(
                        caption,
                        reply_markup=keyboard,
                        disable_web_page_preview=True,
                        parse_mode="HTML" if bot_custom_message else None
                    )
                
                # Запускаем/обновляем напоминания
                await start_reminders(bot_id, user_id, callback.message.message_id)
                
                await callback.answer("❌ Вы не подписаны на все каналы!", show_alert=True)
                
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    await callback.answer("✅ Вы уже проверяли подписки", show_alert=False)
                else:
                    logging.error(f"❌ Ошибка обновления сообщения: {e}")
                    await callback.answer("❌ Ошибка проверки подписок", show_alert=True)
        
        except Exception as e:
            logging.error(f"❌ Ошибка в обработчике check_subs: {e}")
            await callback.answer("❌ Ошибка проверки подписок", show_alert=True)

    @router.callback_query(F.data == "main_button")
    async def main_button_callback(callback: CallbackQuery):
        """Обработчик главной кнопки"""
        await callback.answer("🔗 Кнопка работает!", show_alert=True)

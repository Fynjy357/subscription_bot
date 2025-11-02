"""
worker_bot/reminder_manager.py
Управление напоминаниями для пользователей, не подписавшихся на все каналы
"""

import asyncio
import logging
from datetime import datetime, timedelta

# Глобальные переменные для управления напоминаниями
_reminder_tasks = {}  # {(bot_id, user_id): task}
_reminder_messages = {}  # {(bot_id, user_id): message_id}
_reminder_intervals = {}  # {(bot_id, user_id): interval_minutes}

async def send_reminder_message(bot_id: int, user_id: int, message_id: int = None):
    """
    Отправляет напоминание пользователю и планирует следующее
    
    Args:
        bot_id: ID бота
        user_id: ID пользователя
        message_id: ID сообщения для удаления (если есть)
    """
    try:
        # Получаем активного бота
        from .bot_manager import _active_dispatchers
        if bot_id not in _active_dispatchers:
            logging.info(f"⚠️ Бот {bot_id} не активен для отправки напоминания")
            return
        
        bot_data = _active_dispatchers[bot_id]
        bot = bot_data['bot']
        
        # Проверяем подписки пользователя
        from .core import check_user_subscriptions, get_bot_data_for_worker
        not_subscribed_channels, channels_with_names = await check_user_subscriptions(user_id, bot_id)
        
        # Если пользователь подписался на все каналы, останавливаем напоминания
        if not not_subscribed_channels:
            logging.info(f"✅ Пользователь {user_id} подписался на все каналы, останавливаем напоминания")
            await stop_reminders(bot_id, user_id)
            return
        
        # Получаем данные бота
        bot_data_db = await get_bot_data_for_worker(bot_id)
        if not bot_data_db:
            logging.error(f"❌ Не удалось получить данные бота {bot_id}")
            return
        
        bot_custom_message = bot_data_db[5] if bot_data_db[5] else ""  # message
        image_filename = bot_data_db[9] if bot_data_db[9] else ""  # image_filename
        
        # Формируем сообщение с напоминанием
        from .core import get_image_caption, format_subscription_message
        from .keyboards import create_subscription_keyboard
        
        caption = get_image_caption(bot_custom_message, channels_with_names)
        keyboard = create_subscription_keyboard(not_subscribed_channels, channels_with_names)
        
        # Добавляем текст напоминания
        reminder_text = "⏰ **Напоминание:** Вы еще не подписались на все каналы!\n\n"
        
        # Удаляем старое сообщение если есть
        if message_id:
            try:
                await bot.delete_message(chat_id=user_id, message_id=message_id)
                logging.info(f"🗑️ Удалено старое сообщение {message_id} для пользователя {user_id}")
            except Exception as e:
                logging.warning(f"⚠️ Не удалось удалить старое сообщение: {e}")
        
        # Отправляем новое сообщение с напоминанием
        try:
            # Если есть изображение, отправляем его
            if image_filename:
                from main_bot.file_utils import get_bot_image_path
                import os
                
                image_path = get_bot_image_path(bot_id, image_filename)
                if os.path.exists(image_path):
                    from aiogram.types import FSInputFile
                    photo = FSInputFile(image_path)
                    sent_message = await bot.send_photo(
                        chat_id=user_id,
                        photo=photo,
                        caption=f"{reminder_text}{caption}",
                        reply_markup=keyboard,
                        parse_mode="HTML" if bot_custom_message else None
                    )
                else:
                    full_message = f"{reminder_text}{format_subscription_message(bot_custom_message, channels_with_names)}"
                    sent_message = await bot.send_message(
                        chat_id=user_id,
                        text=full_message,
                        reply_markup=keyboard,
                        disable_web_page_preview=True,
                        parse_mode="HTML" if bot_custom_message else None
                    )
            else:
                full_message = f"{reminder_text}{format_subscription_message(bot_custom_message, channels_with_names)}"
                sent_message = await bot.send_message(
                    chat_id=user_id,
                    text=full_message,
                    reply_markup=keyboard,
                    disable_web_page_preview=True,
                    parse_mode="HTML" if bot_custom_message else None
                )
            
            # Сохраняем ID нового сообщения
            _reminder_messages[(bot_id, user_id)] = sent_message.message_id
            logging.info(f"🔔 Отправлено напоминание пользователю {user_id}, следующее через 10 минут")
            
            # Планируем следующее напоминание через 10 минут
            await schedule_next_reminder(bot_id, user_id, sent_message.message_id)
            
        except Exception as e:
            logging.error(f"❌ Ошибка отправки напоминания пользователю {user_id}: {e}")
            
    except Exception as e:
        logging.error(f"❌ Общая ошибка в send_reminder_message: {e}")

async def schedule_next_reminder(bot_id: int, user_id: int, message_id: int):
    """
    Планирует следующее напоминание через 10 минут
    
    Args:
        bot_id: ID бота
        user_id: ID пользователя
        message_id: ID сообщения для удаления
    """
    try:
        # Отменяем предыдущую задачу если есть
        await stop_reminders(bot_id, user_id)
        
        # Создаем новую задачу на 10 минут (600 секунд)
        task = asyncio.create_task(
            send_reminder_after_delay(bot_id, user_id, message_id, 600)  # 10 минут = 600 секунд
        )
        
        _reminder_tasks[(bot_id, user_id)] = task
        logging.info(f"⏰ Запланировано следующее напоминание для пользователя {user_id} через 10 минут")
        
    except Exception as e:
        logging.error(f"❌ Ошибка планирования напоминания: {e}")

async def send_reminder_after_delay(bot_id: int, user_id: int, message_id: int, delay_seconds: int):
    """
    Отправляет напоминание через указанное время
    
    Args:
        bot_id: ID бота
        user_id: ID пользователя
        message_id: ID сообщения для удаления
        delay_seconds: Задержка в секундах
    """
    try:
        await asyncio.sleep(delay_seconds)
        await send_reminder_message(bot_id, user_id, message_id)
        
    except asyncio.CancelledError:
        logging.info(f"✅ Напоминание для пользователя {user_id} отменено")
    except Exception as e:
        logging.error(f"❌ Ошибка в send_reminder_after_delay: {e}")

async def start_reminders(bot_id: int, user_id: int, message_id: int = None):
    """
    Запускает цикл напоминаний для пользователя
    
    Args:
        bot_id: ID бота
        user_id: ID пользователя
        message_id: ID сообщения для удаления при первом напоминании
    """
    try:
        logging.info(f"🔔 Запуск напоминаний для пользователя {user_id}")
        
        # Проверяем, не запущены ли уже напоминания
        if (bot_id, user_id) in _reminder_tasks:
            logging.info(f"ℹ️ Напоминания для пользователя {user_id} уже запущены")
            return
        
        # Сохраняем ID сообщения для будущего удаления
        if message_id:
            _reminder_messages[(bot_id, user_id)] = message_id
        
        # Планируем первое напоминание через 10 минут
        await schedule_next_reminder(bot_id, user_id, message_id)
        logging.info(f"⏰ Первое напоминание запланировано для пользователя {user_id} через 10 минут")
        
    except Exception as e:
        logging.error(f"❌ Ошибка запуска напоминаний: {e}")

async def stop_reminders(bot_id: int, user_id: int):
    """
    Останавливает напоминания для пользователя
    
    Args:
        bot_id: ID бота
        user_id: ID пользователя
    """
    try:
        key = (bot_id, user_id)
        
        # Отменяем задачу если есть
        if key in _reminder_tasks:
            task = _reminder_tasks[key]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            del _reminder_tasks[key]
        
        # Очищаем сообщение
        if key in _reminder_messages:
            del _reminder_messages[key]
        
        logging.info(f"🛑 Остановлены напоминания для пользователя {user_id}")
        
    except Exception as e:
        logging.error(f"❌ Ошибка остановки напоминаний: {e}")

async def stop_all_reminders_for_bot(bot_id: int):
    """
    Останавливает все напоминания для указанного бота
    
    Args:
        bot_id: ID бота
    """
    try:
        keys_to_remove = []
        
        for (b_id, user_id) in list(_reminder_tasks.keys()):
            if b_id == bot_id:
                await stop_reminders(bot_id, user_id)
                keys_to_remove.append((b_id, user_id))
        
        logging.info(f"🛑 Остановлены все напоминания для бота {bot_id} ({len(keys_to_remove)} пользователей)")
        
    except Exception as e:
        logging.error(f"❌ Ошибка остановки всех напоминаний для бота {bot_id}: {e}")

async def stop_all_reminders():
    """
    Останавливает все напоминания для всех ботов
    """
    try:
        keys_to_remove = list(_reminder_tasks.keys())
        
        for (bot_id, user_id) in keys_to_remove:
            await stop_reminders(bot_id, user_id)
        
        logging.info(f"🛑 Остановлены все напоминания ({len(keys_to_remove)} пользователей)")
        
    except Exception as e:
        logging.error(f"❌ Ошибка остановки всех напоминаний: {e}")

def is_reminder_active(bot_id: int, user_id: int) -> bool:
    """
    Проверяет, активны ли напоминания для пользователя
    
    Args:
        bot_id: ID бота
        user_id: ID пользователя
        
    Returns:
        bool: True если напоминания активны
    """
    return (bot_id, user_id) in _reminder_tasks

def get_active_reminders_count(bot_id: int = None) -> int:
    """
    Возвращает количество активных напоминаний
    
    Args:
        bot_id: ID бота (опционально)
        
    Returns:
        int: Количество активных напоминаний
    """
    if bot_id:
        return len([key for key in _reminder_tasks.keys() if key[0] == bot_id])
    else:
        return len(_reminder_tasks)

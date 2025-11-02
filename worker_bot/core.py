"""
worker_bot/core.py
Основные функции и глобальные переменные для рабочих ботов
"""

import asyncio
import logging
import aiosqlite
from datetime import datetime
from aiogram.exceptions import TelegramBadRequest

# Глобальные переменные для управления ботами
active_bots = {}  # {bot_info.id: {'dp': dp, 'bot': bot, 'bot_id': bot_id}}
active_dispatchers = {}  # {bot_id: {'dp': dp, 'bot': bot}} - оставляем для обратной совместимости

async def _get_bot_channels_for_worker(bot_id: int):
    """Получение каналов бота для рабочих ботов (без проверки владельца)"""
    try:
        async with aiosqlite.connect('subscription_bot.db') as db:
            cursor = await db.execute('''
                SELECT id, channel_link, description, is_active
                FROM channels
                WHERE bot_id = ? AND is_active = TRUE
            ''', (bot_id,))
            channels = await cursor.fetchall()
            return channels
    except Exception as e:
        logging.error(f"❌ Ошибка получения каналов для бота {bot_id}: {e}")
        return []

async def check_user_subscriptions(user_id: int, bot_id: int):
    """
    Проверяет подписки пользователя на каналы
    
    Args:
        user_id: ID пользователя
        bot_id: ID бота
        
    Returns:
        tuple: (not_subscribed_channels, all_channels_with_names)
    """
    # Получаем данные бота чтобы найти владельца
    bot_data = await get_bot_data_for_worker(bot_id)
    if not bot_data:
        logging.error(f"❌ Бот {bot_id} не найден в базе данных")
        return [], []
    
    # Получаем все каналы для этого бота
    channels = await _get_bot_channels_for_worker(bot_id)
    if not channels:
        logging.warning(f"⚠️ Для бота {bot_id} не найдено каналов")
        return [], []
    
    not_subscribed_channels = []
    all_channels_with_names = []
    
    for channel in channels:
        channel_id = channel[1]  # channel_link
        channel_name = channel[2] if channel[2] else channel_id  # description
        
        # Сохраняем все каналы для отображения
        all_channels_with_names.append((channel_id, channel_name))
        
        try:
            # Используем готовую функцию из main_bot_client
            from worker_bot.main_bot_client import get_main_bot
            
            main_bot = get_main_bot()
            if not main_bot:
                logging.error("❌ Основной бот не инициализирован")
                not_subscribed_channels.append(channel_id)
                continue
                
            # Используем метод класса MainBotClient
            is_subscribed = await main_bot.check_user_subscription(user_id, channel_id)
            logging.info(f"📊 Канал {channel_id}, подписан: {is_subscribed}")
            
            if not is_subscribed:
                not_subscribed_channels.append(channel_id)
                
        except Exception as e:
            logging.warning(f"⚠️ Ошибка проверки канала {channel_id}: {e}")
            # Если не можем проверить, считаем что пользователь НЕ подписан
            # но все равно показываем кнопку для этого канала
            not_subscribed_channels.append(channel_id)
    
    logging.info(f"🔍 Проверка завершена. Не подписан на: {len(not_subscribed_channels)} каналов")
    return not_subscribed_channels, all_channels_with_names

def format_subscription_message(custom_message: str, channels_with_names: list):
    """
    Форматирует сообщение с каналами для подписки
    
    Args:
        custom_message: Кастомное сообщение из базы
        channels_with_names: Список каналов с названиями
        
    Returns:
        str: Отформатированное сообщение
    """
    # Начало сообщения с кастомным текстом
    if custom_message and custom_message.strip():
        message = f"{custom_message.strip()}\n\n"
    else:
        message = "Для получения бонуса, подпишись на все группы\n\n"
    
    # Добавляем каналы в формате списка
    message += "📋 Каналы для подписки:\n"
    for channel_id, channel_name in channels_with_names:
        message += f"• {channel_name} ({channel_id})\n"
    
    # Добавляем константный текст
    message += "\nВам необходимо подписаться на все группы и нажать кнопку \"проверить подписки\"\n\n"
    message += "Данный бот работает на @sub_group_bot"
    
    return message

def get_image_caption(custom_message: str, channels_with_names: list):
    """
    Форматирует подпись для изображения
    
    Args:
        custom_message: Кастомное сообщение из базы
        channels_with_names: Список каналов с названиями
        
    Returns:
        str: Отформатированная подпись для изображения
    """
    # Начало сообщения с кастомным текстом
    if custom_message and custom_message.strip():
        caption = f"{custom_message.strip()}\n\n"
    else:
        caption = "Для получения бонуса, подпишись на все группы\n\n"
    
    # Добавляем каналы в формате списка
    caption += "📋 Каналы для подписки:\n"
    for channel_id, channel_name in channels_with_names:
        caption += f"• {channel_name} ({channel_id})\n"
    
    # Добавляем константный текст
    caption += "\nВам необходимо подписаться на все группы и нажать кнопку \"проверить подписки\"\n\n"
    caption += "Данный бот работает на @sub_group_bot"
    
    return caption

def format_materials_message(button_url: str, file_id: str, file_type: str):
    """
    Форматирует сообщение с материалами после успешной подписки
    
    Args:
        button_url: Ссылка или текст из базы данных
        file_id: ID файла
        file_type: Тип файла
        
    Returns:
        str: Отформатированное сообщение с материалами
    """
    materials_text = "📚 Ваши материалы:\n\n"
    
    # Добавляем текст из button_url
    if button_url:
        materials_text += f"🔗 {button_url}\n\n"
    
    # Добавляем информацию о файлах
    if file_id and file_type:
        file_type_emoji = {
            'photo': '🖼️',
            'video': '🎬', 
            'document': '📄'
        }
        materials_text += f"{file_type_emoji.get(file_type, '📎')} Файл прикреплен ниже\n\n"
    
    # Добавляем контактную информацию организатора
    materials_text += "Если остались вопросы, то вы можете обратиться к организатору:\n"
    materials_text += "@username\n"
    materials_text += "telegram_id"
    
    return materials_text

async def get_bot_data_for_worker(bot_id: int):
    """
    Получает данные бота из базы данных
    
    Args:
        bot_id: ID бота
        
    Returns:
        tuple: Данные бота или None
    """
    try:
        async with aiosqlite.connect('subscription_bot.db') as db:
            cursor = await db.execute('''
                SELECT b.id, b.bot_token, b.bot_username, b.bot_name, b.is_active, 
                       b.message, b.button_url, b.file_id, b.file_type, b.image_filename,
                       b.material_sent_at  -- ДОБАВЛЕНО ПОЛЕ
                FROM bots b 
                WHERE b.id = ? AND b.is_active = TRUE
            ''', (bot_id,))
            bot_data = await cursor.fetchone()
            return bot_data
    except Exception as e:
        logging.error(f"❌ Ошибка получения данных бота {bot_id}: {e}")
        return None

async def send_subscription_success_message(message, bot_data, user_id):
    """
    Отправляет сообщение об успешной подписке в зависимости от material_sent_at
    
    Args:
        message: Объект сообщения для отправки
        bot_data: Данные бота из базы
        user_id: ID пользователя
    """
    # Распаковываем данные бота
    bot_id, bot_token, bot_username, bot_name, is_active, bot_message, button_url, file_id, file_type, image_filename, material_sent_at = bot_data
    
    # Если material_sent_at заполнен
    if material_sent_at:
        try:
            # Парсим дату
            date_obj = datetime.fromisoformat(material_sent_at)
            formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
            
            welcome_text = (
                "✅ Отлично! Вы подписаны на всех авторов! Спасибо, что поддерживаете нас.\n\n"
                f"📅 Материалы придут вам {formatted_date}\n\n"
                "⚠️ Если ВЫ отписались, то рассылка не сможет найти адресата☹️"
            )
            
        except Exception as e:
            logging.error(f"❌ Ошибка парсинга даты {material_sent_at}: {e}")
            welcome_text = (
                "✅ Отлично! Вы подписаны на всех авторов! Спасибо, что поддерживаете нас.\n\n"
                f"📅 Материалы придут вам {material_sent_at}\n\n"
                "⚠️ Если ВЫ отписались, то рассылка не сможет найти адресата☹️"
            )
    else:
        # Если material_sent_at не заполнен
        welcome_text = (
            "✅ Отлично! Вы подписаны на всех авторов! Спасибо, что поддерживаете нас.\n\n"
            "🔗 Как и обещали, Ваша ссылка на материалы."
        )
        
        # Если есть ссылка, добавляем ее
        if button_url:
            welcome_text += f"\n\n{button_url}"
    
    # Отправляем сообщение с медиа или без
    from .media_utils import send_media_with_message
    if file_id and file_type:
        await send_media_with_message(message, file_id, file_type, welcome_text, None)
    else:
        await message.answer(
            welcome_text,
            reply_markup=None,  # Убираем клавиатуру полностью
            parse_mode=None
        )
    
    # Если material_sent_at заполнен, планируем отправку материалов
    if material_sent_at:
        await schedule_material_delivery(bot_id, user_id, button_url, file_id, file_type, material_sent_at)

async def schedule_material_delivery(bot_id: int, user_id: int, button_url: str, file_id: str, file_type: str, material_sent_at: str):
    """
    Планирует отправку материалов в указанную дату
    
    Args:
        bot_id: ID бота
        user_id: ID пользователя
        button_url: Ссылка на материалы
        file_id: ID файла
        file_type: Тип файла
        material_sent_at: Дата отправки материалов
    """
    try:
        # Парсим дату
        send_date = datetime.fromisoformat(material_sent_at)
        now = datetime.now()
        
        # Вычисляем задержку до отправки
        delay_seconds = (send_date - now).total_seconds()
        
        if delay_seconds > 0:
            logging.info(f"⏰ Планируем отправку материалов для пользователя {user_id} через {delay_seconds} секунд")
            
            # Создаем задачу на отправку
            asyncio.create_task(
                send_materials_at_scheduled_time(bot_id, user_id, button_url, file_id, file_type, delay_seconds)
            )
        else:
            logging.warning(f"⚠️ Дата отправки материалов уже прошла: {material_sent_at}")
            
    except Exception as e:
        logging.error(f"❌ Ошибка планирования отправки материалов: {e}")

async def send_materials_at_scheduled_time(bot_id: int, user_id: int, button_url: str, file_id: str, file_type: str, delay_seconds: float):
    """
    Отправляет материалы через указанное время
    
    Args:
        bot_id: ID бота
        user_id: ID пользователя
        button_url: Ссылка на материалы
        file_id: ID файла
        file_type: Тип файла
        delay_seconds: Задержка в секундах
    """
    try:
        # Ждем указанное время
        await asyncio.sleep(delay_seconds)
        
        # Получаем активного бота
        from .bot_manager import _active_dispatchers
        if bot_id not in _active_dispatchers:
            logging.error(f"❌ Бот {bot_id} не активен для отправки материалов")
            return
        
        bot_data = _active_dispatchers[bot_id]
        bot = bot_data['bot']
        
        # Проверяем, что пользователь все еще подписан на все каналы
        not_subscribed_channels, _ = await check_user_subscriptions(user_id, bot_id)
        
        if not_subscribed_channels:
            logging.info(f"⚠️ Пользователь {user_id} отписался от каналов, материалы не отправляем")
            return
        
        # Формируем сообщение с материалами
        materials_text = (
            "📅 Как и обещали, Ваша ссылка на материалы.\n\n"
            f"{button_url if button_url else '🔗 Ссылка на материалы'}"
        )
        
        # Отправляем материалы
        from .media_utils import send_media_with_message
        
        # Создаем временный объект сообщения для отправки
        class TempMessage:
            def __init__(self, bot, user_id):
                self.bot = bot
                self.user_id = user_id
            
            async def answer(self, text, reply_markup=None, parse_mode=None):
                await self.bot.send_message(
                    chat_id=self.user_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            
            async def answer_photo(self, photo, caption, reply_markup=None, parse_mode=None):
                await self.bot.send_photo(
                    chat_id=self.user_id,
                    photo=photo,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            
            async def answer_video(self, video, caption, reply_markup=None, parse_mode=None):
                await self.bot.send_video(
                    chat_id=self.user_id,
                    video=video,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            
            async def answer_document(self, document, caption, reply_markup=None, parse_mode=None):
                await self.bot.send_document(
                    chat_id=self.user_id,
                    document=document,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
        
        temp_message = TempMessage(bot, user_id)
        
        if file_id and file_type:
            await send_media_with_message(temp_message, file_id, file_type, materials_text, None)
        else:
            await temp_message.answer(materials_text, reply_markup=None, parse_mode=None)
        
        logging.info(f"✅ Материалы отправлены пользователю {user_id}")
        
    except Exception as e:
        logging.error(f"❌ Ошибка отправки материалов пользователю {user_id}: {e}")

"""
main_bot/file_utils.py
Утилиты для работы с файлами в основном боте
"""

import os
import uuid
import logging
from pathlib import Path
from aiogram.types import Message

# Базовая папка для медиа
MEDIA_BASE = "media"
BOT_IMAGES_DIR = f"{MEDIA_BASE}/bot_images"

def ensure_directories():
    """Создает необходимые директории"""
    os.makedirs(BOT_IMAGES_DIR, exist_ok=True)
    os.makedirs(f"{MEDIA_BASE}/temp", exist_ok=True)
    os.makedirs(f"{MEDIA_BASE}/backups", exist_ok=True)

async def save_bot_image_from_main_bot(bot_id: int, message: Message) -> str:
    """
    Сохраняет изображение бота на сервер (только через основной бот)
    
    Args:
        bot_id: ID бота
        message: Сообщение с изображением из основного бота
        
    Returns:
        str: Имя файла на сервере
    """
    ensure_directories()
    
    # Создаем папку для бота
    bot_dir = f"{BOT_IMAGES_DIR}/bot_{bot_id}"
    os.makedirs(bot_dir, exist_ok=True)
    
    if message.photo:
        # Берем самое большое фото
        photo = message.photo[-1]
        file_info = await message.bot.get_file(photo.file_id)
        file_ext = ".jpg"
    elif message.document:
        file_info = await message.bot.get_file(message.document.file_id)
        file_ext = os.path.splitext(message.document.file_name or "image.jpg")[1]
    else:
        raise ValueError("Сообщение не содержит изображение")
    
    # Генерируем уникальное имя файла
    filename = f"image_{uuid.uuid4().hex}{file_ext}"
    file_path = f"{bot_dir}/{filename}"
    
    # Скачиваем файл
    await message.bot.download_file(file_info.file_path, file_path)
    
    logging.info(f"💾 Изображение сохранено основным ботом: {file_path}")
    return filename

def get_bot_image_path(bot_id: int, filename: str) -> str:
    """
    Возвращает полный путь к изображению бота
    
    Args:
        bot_id: ID бота
        filename: Имя файла
        
    Returns:
        str: Полный путь к файлу
    """
    return f"{BOT_IMAGES_DIR}/bot_{bot_id}/{filename}"

def delete_bot_image(bot_id: int, filename: str) -> bool:
    """
    Удаляет изображение бота
    
    Args:
        bot_id: ID бота
        filename: Имя файла
        
    Returns:
        bool: Успешно ли удаление
    """
    file_path = get_bot_image_path(bot_id, filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.info(f"🗑️ Удалено изображение: {file_path}")
            return True
    except Exception as e:
        logging.error(f"❌ Ошибка удаления изображения: {e}")
    return False

def get_bot_images_list(bot_id: int) -> list:
    """
    Возвращает список изображений бота
    
    Args:
        bot_id: ID бота
        
    Returns:
        list: Список имен файлов
    """
    bot_dir = f"{BOT_IMAGES_DIR}/bot_{bot_id}"
    if not os.path.exists(bot_dir):
        return []
    
    return [f for f in os.listdir(bot_dir) if os.path.isfile(os.path.join(bot_dir, f))]

def cleanup_old_images(bot_id: int, keep_filename: str = None):
    """
    Удаляет старые изображения бота, оставляя только указанное
    
    Args:
        bot_id: ID бота
        keep_filename: Имя файла, который нужно сохранить
    """
    images = get_bot_images_list(bot_id)
    for filename in images:
        if filename != keep_filename:
            delete_bot_image(bot_id, filename)
            logging.info(f"🗑️ Удалено старое изображение: {filename}")

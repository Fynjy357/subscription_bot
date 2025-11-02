# config.py
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

# ID супер-администраторов (опционально)
SUPER_ADMIN_IDS = []
try:
    admin_ids = os.getenv('SUPER_ADMIN_IDS', '')
    if admin_ids:
        SUPER_ADMIN_IDS = [int(x.strip()) for x in admin_ids.split(',') if x.strip()]
except ValueError as e:
    logging.warning(f"⚠️ Ошибка парсинга SUPER_ADMIN_IDS: {e}")

# Настройки базы данных
DATABASE_NAME = os.getenv('DATABASE_NAME', 'subscription_bot.db')

# Лимиты
MAX_CHANNELS_PER_BOT = int(os.getenv('MAX_CHANNELS_PER_BOT', '10'))

# Настройки вебхуков
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', '89.223.125.102')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '8443'))

# Валидация обязательных переменных
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не установлен в .env файле")

logging.info("✅ Конфигурация загружена")

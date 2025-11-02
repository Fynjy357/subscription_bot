# payment_config.py
import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Настройки YooKassa
YOOMONEY_SHOP_ID = os.getenv('YOOMONEY_SHOP_ID')
YOOMONEY_SECRET_KEY = os.getenv('YOOMONEY_SECRET_KEY')

# Вебхук настройки
WEBHOOK_HOST = os.getenv('WEBHOOK_HOST', '89.223.125.102')
WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', '8443'))
WEBHOOK_BASE_URL = f"http://{WEBHOOK_HOST}:{WEBHOOK_PORT}"

# Тарифы для покупки ботов
TARIFFS = {
    1: {
        'amount': 500,
        'bots_count': 10,
        'description': '+10 групп'
    },
    2: {
        'amount': 900,
        'bots_count': 20,
        'description': '+20 групп'
    },
    3: {
        'amount': 1700,
        'bots_count': 50,
        'description': '+50 групп'
    }
}

# Информационное сообщение
if not YOOMONEY_SHOP_ID or YOOMONEY_SHOP_ID == 'test_shop_id':
    logging.info("🔧 Платежная система YooKassa в тестовом режиме")
else:
    logging.info("✅ Платежная система YooKassa настроена")

logging.info(f"🌐 Вебхук URL: {WEBHOOK_BASE_URL}/webhook/yookassa")

"""
main_bot/handlers/__init__.py
Инициализация обработчиков
"""

import logging
import sys
import os
from aiogram import Dispatcher, Router

# Добавляем корневую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logger = logging.getLogger(__name__)

async def setup_handlers(dp: Dispatcher, yookassa_service=None):
    """Настройка всех обработчиков"""
    # Создаем общий роутер
    router = Router()
    
    try:
        # Стартовые обработчики
        from main_bot.handlers.start import setup_start_handlers
        await setup_start_handlers(router)
        logger.info("✅ Стартовые обработчики настроены")
        
        # Управление ботами
        from main_bot.handlers.bot_management import setup_bot_management_handlers
        await setup_bot_management_handlers(router)
        logger.info("✅ Обработчики управления ботами настроены")
        
        # Управление каналами
        from main_bot.handlers.channel_management import setup_channel_management_handlers
        await setup_channel_management_handlers(router)
        logger.info("✅ Обработчики управления каналами настроены")
        
        # Управление сообщениями
        from main_bot.handlers.message_management import setup_message_management_handlers
        await setup_message_management_handlers(router)
        logger.info("✅ Обработчики управления сообщениями настроены")
        
        # Управление кнопками
        from main_bot.handlers.button_management import setup_button_management_handlers
        await setup_button_management_handlers(router)
        logger.info("✅ Обработчики управления кнопками настроены")
        
        # Управление файлами
        from main_bot.handlers.file_management import setup_file_management_handlers
        await setup_file_management_handlers(router)
        logger.info("✅ Обработчики управления файлами настроены")
        
        # Управление изображениями - ДОБАВЛЕНО
        from main_bot.handlers.image_management import setup_image_management_handlers
        await setup_image_management_handlers(router)
        logger.info("✅ Обработчики управления изображениями настроены")
        
        # Управление датой рассылки материала - ДОБАВЛЕНО
        from main_bot.handlers.material_date_management import setup_material_date_handlers
        await setup_material_date_handlers(router)
        logger.info("✅ Обработчики управления датой рассылки настроены")
        
        # Платежи
        if yookassa_service:
            from main_bot.handlers.payment_handlers import setup_payment_handlers
            await setup_payment_handlers(router, yookassa_service)
            logger.info("✅ Обработчики платежей настроены")
        else:
            logger.warning("⚠️ YooKassa сервис не передан, платежные обработчики отключены")
        
        # Администратор
        from main_bot.handlers.admin_handlers import setup_admin_handlers
        await setup_admin_handlers(router)
        logger.info("✅ Обработчики администратора настроены")
        
    except Exception as e:
        logger.error(f"❌ Ошибка настройки обработчиков: {e}")
        raise
    
    # Включаем роутер в диспетчер
    dp.include_router(router)
    logger.info("🎯 Все обработчики настроены успешно")

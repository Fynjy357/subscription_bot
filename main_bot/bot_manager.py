"""
main_bot/bot_manager.py
Управление основным ботом
"""

import logging
import asyncio
import sys
import os
from aiogram import Bot, Dispatcher


# Добавляем корневую директорию в путь для импортов
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

# Глобальные переменные для управления основным ботом
_main_bot_task = None
_main_bot_dp = None
_main_bot_instance = None

async def start_main_bot(yookassa_service=None):
    """Запуск основного бота"""
    global _main_bot_task, _main_bot_dp, _main_bot_instance
    
    bot = None
    try:
        # Используем абсолютный импорт с правильным именем переменной
        from config import BOT_TOKEN
        
        bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
        _main_bot_instance = bot
        dp = Dispatcher()
        _main_bot_dp = dp
        
        # Настройка всех хендлеров
        try:
            from main_bot.handlers import setup_handlers
            await setup_handlers(dp, yookassa_service)
            logger.info("✅ Все обработчики основного бота настроены")
        except ImportError as e:
            logger.error(f"❌ Ошибка импорта хендлеров: {e}")
            return
        
        # Запускаем polling
        logger.info("🎯 Основной бот запускает polling...")
        await dp.start_polling(bot)
        
    except asyncio.CancelledError:
        logger.info("✅ Основной бот получил сигнал отмены")
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка в основном боте: {e}")
        raise
    finally:
        if bot:
            await bot.session.close()
            _main_bot_instance = None

async def stop_main_bot():
    """Остановка основного бота с улучшенной обработкой"""
    global _main_bot_dp, _main_bot_instance
    
    try:
        logging.info("🛑 Остановка основного бота...")
        
        if _main_bot_dp:
            # Останавливаем polling
            _main_bot_dp._polling = False
            logging.info("✅ Polling основного бота остановлен")
        
        if _main_bot_instance:
            try:
                await _main_bot_instance.session.close()
                # Даем время на корректное закрытие
                await asyncio.sleep(1.0)
                logging.info("✅ Сессия основного бота закрыта")
            except Exception as e:
                logging.warning(f"⚠️ Ошибка при закрытии сессии основного бота: {e}")
            finally:
                _main_bot_instance = None
            
    except Exception as e:
        logging.error(f"❌ Ошибка при остановке основного бота: {e}")

def get_main_bot():
    """Получить экземпляр основного бота"""
    return _main_bot_instance

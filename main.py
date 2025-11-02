# main.py
import asyncio
import logging
import sys
import os
import signal

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

from database import init_db, get_all_active_bots
from main_bot.bot_manager import start_main_bot, stop_main_bot
from payment_config import YOOMONEY_SHOP_ID, YOOMONEY_SECRET_KEY
from yookassa_service import YooKassaService
from payment_manager import PaymentManager
from webhook_server import webhook_server  # ИСПРАВЛЕНО: импортируем экземпляр

# Глобальные переменные
payment_manager = None
webhook_runner = None
shutdown_event = asyncio.Event()

def signal_handler(signum, frame):
    """Обработчик сигналов завершения"""
    logger.info("🛑 Получен сигнал завершения...")
    shutdown_event.set()

async def graceful_shutdown():
    """Корректное завершение работы с улучшенной обработкой"""
    logger.info("🛑 Корректное завершение работы...")
    
    try:
        # Сначала останавливаем всех воркер-ботов
        try:
            from worker_bot.bot_manager import stop_all_worker_bots
            logger.info("🛑 Остановка воркер-ботов...")
            await stop_all_worker_bots()
            await asyncio.sleep(3.0)  # Даем больше времени на корректную остановку
            logger.info("✅ Все воркер-боты остановлены")
        except ImportError as e:
            logger.warning(f"⚠️ Модуль worker_bot не найден: {e}")
        except Exception as e:
            logger.error(f"❌ Ошибка при остановке воркер-ботов: {e}")
        
        # Затем останавливаем мониторинг платежей
        if payment_manager:
            await payment_manager.stop_monitoring()
            logger.info("✅ Мониторинг платежей остановлен")
        
        # Останавливаем вебхук сервер (ИСПРАВЛЕНО)
        logger.info("🛑 Остановка вебхук сервера...")
        await webhook_server.stop()  # ИСПРАВЛЕНО: используем метод экземпляра
        logger.info("✅ Вебхук сервер остановлен")
        
        # В последнюю очередь останавливаем основной бот
        logger.info("🛑 Остановка основного бота...")
        await stop_main_bot()
        await asyncio.sleep(2.0)  # Даем время на корректную остановку
        logger.info("✅ Основной бот остановлен")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при завершении работы: {e}")
    
    logger.info("👋 Завершение работы...")

async def validate_bot_tokens(active_bots):
    """Валидирует токены ботов перед запуском"""
    valid_bots = []
    
    for bot_data in active_bots:
        if len(bot_data) >= 5:
            bot_id, bot_token, bot_username, bot_name, is_active = bot_data
            
            if not bot_token or not is_active:
                continue
                
            try:
                from aiogram import Bot
                test_bot = Bot(token=bot_token)
                bot_info = await test_bot.get_me()
                await test_bot.session.close()
                
                valid_bots.append(bot_data)
                logger.info(f"✅ Токен бота @{bot_username} валиден")
                
            except Exception as e:
                logger.error(f"❌ Невалидный токен бота ID {bot_id}: {e}")
    
    return valid_bots

async def start_worker_bots(valid_bots):
    """Запускает рабочих ботов с обработкой ошибок"""
    # Пробуем импортировать модуль worker_bot
    try:
        from worker_bot.bot_manager import start_worker_bot
        worker_bot_available = True
    except ImportError as e:
        logger.warning(f"⚠️ Модуль worker_bot не найден: {e}")
        worker_bot_available = False
        return
    
    if not worker_bot_available:
        return
    
    # Запускаем всех валидных ботов
    logger.info("▶️ Запуск рабочих ботов...")
    for bot_data in valid_bots:
        bot_id, bot_token, bot_username, bot_name, is_active = bot_data
        try:
            await start_worker_bot(bot_token, bot_id)
            logger.info(f"▶️ Запущен бот ID {bot_id} (@{bot_username})")
            await asyncio.sleep(1)  # Небольшая задержка между запусками
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота ID {bot_id}: {e}")

async def main():
    """Главная функция запуска"""
    global payment_manager, webhook_runner
    
    try:
        logger.info("=" * 50)
        logger.info("🚀 ЗАПУСК БОТА")
        logger.info("=" * 50)
        
        # Регистрируем обработчики сигналов
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("🔍 Проверка конфигурации...")
        
        # Инициализируем базу данных
        logger.info("🗄️ Инициализация базы данных...")
        await init_db()
        logger.info("✅ База данных инициализирована")
        
        # Инициализация платежной системы
        logger.info("💰 Инициализация платежной системы...")
        yookassa_service = YooKassaService(YOOMONEY_SHOP_ID, YOOMONEY_SECRET_KEY)
        payment_manager = PaymentManager(yookassa_service)
        
        # Запускаем мониторинг платежей
        logger.info("🔍 Запуск мониторинга платежей...")
        asyncio.create_task(payment_manager.start_monitoring())
        
        # Запускаем вебхук сервер (ИСПРАВЛЕНО)
        logger.info("🌐 Запуск вебхук сервера...")
        webhook_runner = await webhook_server.start()  # ИСПРАВЛЕНО: используем метод экземпляра
        logger.info("✅ Вебхук сервер запущен")
        
        # Загружаем всех активных ботов из БД
        logger.info("📊 Загрузка активных ботов из БД...")
        active_bots = await get_all_active_bots()
        logger.info(f"📊 Найдено активных ботов в БД: {len(active_bots)}")
        
        # Валидируем токены ботов
        logger.info("🔐 Валидация токенов ботов...")
        valid_bots = await validate_bot_tokens(active_bots)
        logger.info(f"✅ Валидных ботов для запуска: {len(valid_bots)}")
        
        if len(valid_bots) < len(active_bots):
            logger.warning(f"⚠️ {len(active_bots) - len(valid_bots)} ботов имеют невалидные токены")
        
        # СНАЧАЛА запускаем основной бот
        logger.info("🎯 Запуск основного бота...")
        main_bot_task = asyncio.create_task(start_main_bot(yookassa_service))
        
        # Даем основному боту время на инициализацию
        await asyncio.sleep(3)
        logger.info("✅ Основной бот инициализирован")
        
        # ИНИЦИАЛИЗИРУЕМ ОСНОВНОЙ БОТ ДЛЯ ПРОВЕРКИ ПОДПИСОК
        try:
            from worker_bot.main_bot_client import init_main_bot
            from config import BOT_TOKEN
            
            logger.info("🔧 Инициализация основного бота для проверки подписок...")
            await init_main_bot(BOT_TOKEN)
            logger.info("✅ Основной бот для проверки подписок инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации основного бота для проверки подписок: {e}")
        
        # ПОТОМ запускаем рабочих ботов
        await start_worker_bots(valid_bots)
        
        # Ждем либо завершения основного бота, либо сигнала shutdown
        shutdown_task = asyncio.create_task(shutdown_event.wait())
        
        done, pending = await asyncio.wait(
            [main_bot_task, shutdown_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Отменяем оставшиеся задачи
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
    except KeyboardInterrupt:
        logger.info("🛑 Получен Ctrl+C...")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка при запуске: {e}")
        import traceback
        logger.error(f"💥 Трассировка ошибки: {traceback.format_exc()}")
    finally:
        await graceful_shutdown()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Завершение по Ctrl+C")
    except Exception as e:
        logger.error(f"💥 Необработанная ошибка: {e}")
        import traceback
        logger.error(f"💥 Трассировка ошибки: {traceback.format_exc()}")

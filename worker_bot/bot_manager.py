"""
worker_bot/bot_manager.py
Управление запуском и остановкой рабочих ботов
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from .core import active_bots
from .router import create_worker_router
from database import get_active_bot_channels
from .reminder_manager import stop_all_reminders_for_bot

# Глобальные переменные для управления задачами ботов
_active_tasks = {}  # {bot_id: task}
_active_dispatchers = {}  # {bot_id: {'dp': dp, 'bot': bot}}
_bot_start_locks = {}  # ЗАЩИТА ОТ ПОВТОРНОГО ЗАПУСКА: {bot_id: lock}

async def start_worker_bot(bot_token: str, bot_id: int):
    """
    Запускает рабочего бота с защитой от повторного запуска
    
    Args:
        bot_token: Токен бота
        bot_id: ID бота в базе данных
    """
    # Создаем лок для этого бота, если его нет
    if bot_id not in _bot_start_locks:
        _bot_start_locks[bot_id] = asyncio.Lock()
    
    async with _bot_start_locks[bot_id]:
        try:
            # Останавливаем бота если он уже запущен
            if bot_id in _active_tasks:
                logging.info(f"ℹ️ Бот {bot_id} уже запущен, останавливаем предыдущий экземпляр")
                await stop_worker_bot(bot_id)
                await asyncio.sleep(2)  # Даем время на корректную остановку
            
            bot = Bot(token=bot_token, parse_mode="HTML")
            dp = Dispatcher()
            
            # Создаем и добавляем роутер с привязанными каналами
            worker_router = create_worker_router(bot_id)
            dp.include_router(worker_router)
            
            # Сохраняем ссылку на бота
            bot_info = await bot.get_me()
            active_bots[bot_info.id] = {'dp': dp, 'bot': bot, 'bot_id': bot_id}
            _active_dispatchers[bot_id] = {'dp': dp, 'bot': bot}
            
            # Получаем количество активных каналов
            channels = await get_active_bot_channels(bot_id)
            
            logging.info(f"🚀 Запуск рабочего бота @{bot_info.username} (ID: {bot_id}) с {len(channels)} активными каналами")
            
            # Запускаем polling в отдельной задаче
            task = asyncio.create_task(_run_polling(bot, dp, bot_id))
            _active_tasks[bot_id] = task
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Ошибка запуска рабочего бота {bot_id}: {e}")
            return False

async def _run_polling(bot: Bot, dp: Dispatcher, bot_id: int):
    """
    Запускает стандартный polling для рабочего бота
    """
    try:
        # Используем стандартный polling aiogram
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logging.info(f"✅ Рабочий бот {bot_id} получил сигнал отмены")
    except Exception as e:
        # Игнорируем ошибки, связанные с остановкой polling
        error_msg = str(e).lower()
        if any(term in error_msg for term in ['polling', 'stopped', 'cancelled', 'closed']):
            logging.info(f"✅ Polling бота {bot_id} остановлен")
        else:
            logging.error(f"❌ Ошибка polling для бота {bot_id}: {e}")
    finally:
        # Корректно закрываем ресурсы
        await _cleanup_bot_resources(bot_id)

async def _cleanup_bot_resources(bot_id: int):
    """Корректная очистка ресурсов бота"""
    try:
        # Закрываем сессию бота
        if bot_id in _active_dispatchers:
            bot_data = _active_dispatchers[bot_id]
            if bot_data['bot']:
                try:
                    await bot_data['bot'].session.close()
                    await asyncio.sleep(0.5)  # Даем время на корректное закрытие
                except Exception as e:
                    # Игнорируем ошибки закрытия сессии (обычно это нормально при остановке)
                    if "session is closed" not in str(e).lower():
                        logging.warning(f"⚠️ Ошибка при закрытии сессии бота {bot_id}: {e}")
        
        # Убираем из активных
        if bot_id in _active_tasks:
            del _active_tasks[bot_id]
        if bot_id in _active_dispatchers:
            del _active_dispatchers[bot_id]
        
        # Убираем из active_bots
        for bot_info_id, bot_data in list(active_bots.items()):
            if bot_data.get('bot_id') == bot_id:
                del active_bots[bot_info_id]
                break
                
    except Exception as e:
        logging.error(f"❌ Ошибка очистки ресурсов бота {bot_id}: {e}")

async def stop_worker_bot(bot_id: int):
    """
    Останавливает рабочего бота с улучшенной обработкой ошибок
    """
    try:
        if bot_id not in _active_tasks and bot_id not in _active_dispatchers:
            logging.info(f"ℹ️ Бот {bot_id} уже остановлен")
            return
            
        logging.info(f"🛑 Остановка бота {bot_id}...")
        
        # Останавливаем все напоминания для этого бота
        from .reminder_manager import stop_all_reminders_for_bot
        await stop_all_reminders_for_bot(bot_id)
        
        # Сначала останавливаем диспетчер (это остановит polling)
        if bot_id in _active_dispatchers:
            bot_data = _active_dispatchers[bot_id]
            
            # Останавливаем polling через стандартный метод (await!)
            if hasattr(bot_data['dp'], 'stop_polling'):
                try:
                    await bot_data['dp'].stop_polling() 
                    logging.info(f"✅ Polling бота {bot_id} остановлен")
                except RuntimeError as e:
                    if "not started" in str(e).lower():
                        logging.info(f"ℹ️ Polling бота {bot_id} уже остановлен")
                    else:
                        logging.error(f"❌ Ошибка остановки polling бота {bot_id}: {e}")
                except Exception as e:
                    logging.error(f"❌ Ошибка остановки polling бота {bot_id}: {e}")
        
        # Затем останавливаем задачу polling
        if bot_id in _active_tasks:
            task = _active_tasks[bot_id]
            if not task.done():
                try:
                    task.cancel()
                    # Ждем завершения задачи с таймаутом
                    await asyncio.wait_for(task, timeout=5.0)
                    logging.info(f"✅ Задача бота {bot_id} остановлена")
                except asyncio.CancelledError:
                    pass
                except asyncio.TimeoutError:
                    logging.warning(f"⚠️ Таймаут при остановке задачи бота {bot_id}")
                except Exception as e:
                    logging.error(f"❌ Ошибка при отмене задачи бота {bot_id}: {e}")
        
        # Закрываем сессию бота
        if bot_id in _active_dispatchers:
            bot_data = _active_dispatchers[bot_id]
            if bot_data['bot']:
                try:
                    await bot_data['bot'].session.close()
                    await asyncio.sleep(1.0)  # Даем время на корректное закрытие
                    logging.info(f"✅ Сессия бота {bot_id} закрыта")
                except Exception as e:
                    logging.warning(f"⚠️ Ошибка при закрытии сессии бота {bot_id}: {e}")
        
        # Очищаем ресурсы
        await _cleanup_bot_resources(bot_id)
        
        logging.info(f"✅ Бот {bot_id} полностью остановлен")
        
    except Exception as e:
        logging.error(f"❌ Ошибка при остановке бота {bot_id}: {e}")
        
    except Exception as e:
        # Игнорируем ошибку "Polling is not started"
        if "Polling is not started" in str(e):
            logging.info(f"ℹ️ Бот {bot_id} уже остановлен")
        else:
            logging.error(f"❌ Ошибка при остановке бота {bot_id}: {e}")

async def stop_all_worker_bots():
    """
    Останавливает всех рабочих ботов с улучшенной обработкой
    """
    try:
        bot_ids = list(_active_tasks.keys())
        if not bot_ids:
            logging.info("ℹ️ Нет активных рабочих ботов для остановки")
            return
            
        logging.info(f"🛑 Останавливаем {len(bot_ids)} рабочих ботов...")
        
        # Сначала останавливаем всех диспетчеров (останавливаем polling)
        for bot_id in bot_ids:
            if bot_id in _active_dispatchers:
                bot_data = _active_dispatchers[bot_id]
                if hasattr(bot_data['dp'], 'stop_polling'):
                    try:
                        await bot_data['dp'].stop_polling()
                        logging.info(f"✅ Polling бота {bot_id} остановлен")
                    except RuntimeError as e:
                        if "not started" in str(e).lower():
                            logging.info(f"ℹ️ Polling бота {bot_id} уже остановлен")
                        else:
                            logging.error(f"❌ Ошибка остановки polling бота {bot_id}: {e}")
                    except Exception as e:
                        logging.error(f"❌ Ошибка остановки polling бота {bot_id}: {e}")
        
        # Затем останавливаем ботов последовательно с задержкой
        for bot_id in bot_ids:
            try:
                await stop_worker_bot(bot_id)
                await asyncio.sleep(1.0) 
            except Exception as e:
                logging.error(f"❌ Ошибка остановки бота {bot_id}: {e}")
        
        logging.info(f"✅ Остановлены все рабочие боты ({len(bot_ids)} шт.)")
        
    except Exception as e:
        logging.error(f"❌ Ошибка при остановке всех ботов: {e}")

def get_active_worker_bots():
    """Получение списка активных рабочих ботов"""
    return list(_active_tasks.keys())

def is_worker_bot_running(bot_id: int) -> bool:
    """Проверяет, запущен ли рабочий бот"""
    return bot_id in _active_tasks

async def restart_worker_bot(bot_token: str, bot_id: int):
    """Перезапускает рабочего бота"""
    try:
        logging.info(f"🔄 Перезапуск бота {bot_id}...")
        
        # Останавливаем бота если он запущен
        if is_worker_bot_running(bot_id):
            await stop_worker_bot(bot_id)
            await asyncio.sleep(2) 
        
        # Запускаем бота заново
        success = await start_worker_bot(bot_token, bot_id)
        if success:
            logging.info(f"✅ Бот {bot_id} успешно перезапущен")
        else:
            logging.error(f"❌ Не удалось перезапустить бота {bot_id}")
            
        return success
        
    except Exception as e:
        logging.error(f"❌ Ошибка перезапуска бота {bot_id}: {e}")
        return False

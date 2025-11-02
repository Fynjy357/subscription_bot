"""
worker_bot/router.py
Создание и настройка роутера для рабочих ботов
"""

from aiogram import Router
from .handlers import setup_handlers

def create_worker_router(bot_id: int):
    """
    Создает роутер для рабочего бота с привязанными каналами
    
    Args:
        bot_id: ID бота для которого создается роутер
        
    Returns:
        Router: Настроенный роутер с обработчиками
    """
    router = Router()
    
    # Настраиваем все обработчики для этого роутера
    setup_handlers(router, bot_id)
    
    return router

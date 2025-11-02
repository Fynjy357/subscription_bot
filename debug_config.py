# debug_config.py
import logging
import sys

def setup_logging():
    """Настройка подробного логирования"""
    logging.basicConfig(
        level=logging.DEBUG,  # Изменено на DEBUG для более подробных логов
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('bot_debug.log', encoding='utf-8', mode='w')
        ]
    )
    
    # Уменьшаем логирование для некоторых шумных библиотек
    logging.getLogger('aiogram').setLevel(logging.INFO)
    logging.getLogger('asyncio').setLevel(logging.INFO)
    logging.getLogger('aiohttp').setLevel(logging.INFO)

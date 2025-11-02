# Worker Bot Package

Пакет для управления рабочими ботами проверки подписок на каналы.

## Структура

- `core.py` - Основные функции и глобальные переменные
- `handlers.py` - Обработчики команд и callback'ов
- `keyboards.py` - Клавиатуры и кнопки
- `media_utils.py` - Утилиты для работы с медиа-файлами
- `router.py` - Создание и настройка роутера
- `bot_manager.py` - Управление запуском/остановкой ботов

## Использование

```python
from worker_bot import start_worker_bot, stop_worker_bot, stop_all_worker_bots

# Запуск бота
await start_worker_bot("bot_token", bot_id)

# Остановка бота
await stop_worker_bot(bot_id)

# Остановка всех ботов
await stop_all_worker_bots()

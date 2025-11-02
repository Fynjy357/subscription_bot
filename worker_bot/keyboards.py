"""
worker_bot/keyboards.py
Клавиатуры и кнопки для рабочих ботов
"""

import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def create_subscription_keyboard(not_subscribed_channels: list, all_channels_with_names: list):
    """
    Создает клавиатуру с кнопками для подписки
    
    Args:
        not_subscribed_channels: Список каналов, на которые пользователь НЕ подписан
        all_channels_with_names: Все каналы с названиями (для получения названий)
        
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    # Создаем словарь для быстрого поиска названий каналов
    channel_names = dict(all_channels_with_names)
    
    # Создаем кнопки ТОЛЬКО для каналов, на которые пользователь НЕ подписан
    for channel_id in not_subscribed_channels:
        channel_name = channel_names.get(channel_id, channel_id)
        
        # Создаем кнопку для подписки на канал
        button = InlineKeyboardButton(
            text=f"📢 Подписаться на {channel_name}",
            url=f"https://t.me/{channel_id.lstrip('@')}"
        )
        keyboard.inline_keyboard.append([button])
    
    # Добавляем кнопку проверки подписок (всегда)
    check_button = InlineKeyboardButton(
        text="✅ Проверить подписки",
        callback_data="check_subs"  # Убедитесь что callback_data совпадает с обработчиком
    )
    keyboard.inline_keyboard.append([check_button])
    
    logging.info(f"⌨️ Создана клавиатура с {len(not_subscribed_channels)} кнопками подписки")
    return keyboard


def main_menu_kb(button_url: str = ""):
    """
    Клавиатура главного меню с кнопкой из базы данных
    
    Args:
        button_url: Ссылка или текст для кнопки
        
    Returns:
        InlineKeyboardMarkup: Клавиатура главного меню
    """
    buttons = []
    if button_url:
        # Если ссылка начинается с http, это URL-кнопка
        if button_url.startswith('http'):
            buttons.append([InlineKeyboardButton(text="🔗 Перейти", url=button_url)])
        else:
            # Иначе это текст для кнопки (можно использовать для callback)
            buttons.append([InlineKeyboardButton(text=button_url, callback_data="main_button")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

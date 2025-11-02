"""
main_bot/keyboards.py
Клавиатуры для основного бота
"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database import get_user_bots, is_super_admin

async def get_main_user_keyboard(user_id: int):
    """Главная клавиатура пользователя"""
    buttons = [
        [InlineKeyboardButton(text="🤖 Добавить бота", callback_data="add_bot")],
        [InlineKeyboardButton(text="⚙️ Настроить боты", callback_data="configure_bots")],
        [InlineKeyboardButton(text="⏹️ Остановить бота", callback_data="delete_bot")],
        [InlineKeyboardButton(text="💰 Купить каналы", callback_data="buy_bots")]
    ]
    
    # Добавляем кнопку для супер-админов
    if await is_super_admin(user_id):
        buttons.append([InlineKeyboardButton(text="⚡ Админ-панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_bots_list_keyboard(user_id: int):
    """Клавиатура со списком ботов для настройки"""
    bots = await get_user_bots(user_id)
    
    keyboard = []
    for bot in bots:
        # Распаковываем все 10 значений (теперь image_filename вместо image_file_id)
        bot_id, bot_token, bot_username, bot_name, is_active, bot_message, button_url, file_id, file_type, image_filename, material_sent_at = bot

        status = "🟢" if is_active else "🔴"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {bot_name} (@{bot_username})", 
                callback_data=f"bot_{bot_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def get_delete_bots_list_keyboard(user_id: int):
    """Клавиатура со списком ботов для удаления"""
    bots = await get_user_bots(user_id)
    
    keyboard = []
    for bot in bots:
        # Распаковываем все 10 значений (включая image_file_id)
        bot_id, bot_token, bot_username, bot_name, is_active, bot_message, button_url, file_id, file_type, image_filename, material_sent_at = bot

        status = "🟢" if is_active else "🔴"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {bot_name} (@{bot_username})", 
                callback_data=f"manage_bot_{bot_id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_bot_management_keyboard(bot_id: int):
    """Клавиатура управления ботом"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Добавить канал", callback_data=f"add_channel_{bot_id}"),
            InlineKeyboardButton(text="📋 Список каналов", callback_data=f"list_channels_{bot_id}")
        ],
        [
            InlineKeyboardButton(text="📝 Сообщение", callback_data=f"edit_message_{bot_id}"),
            InlineKeyboardButton(text="🔗 Ссылка", callback_data=f"edit_button_{bot_id}")
        ],
        [
            InlineKeyboardButton(text="🖼️ Прикрепить изображение", callback_data=f"attach_image_{bot_id}"),
            InlineKeyboardButton(text="📅 Дата рассылки", callback_data=f"material_date_{bot_id}")
        ],
        # Файл временно закомментирован
        # [
        #     InlineKeyboardButton(text="📎 Файл", callback_data=f"edit_file_{bot_id}")
        # ],
        [
            InlineKeyboardButton(text="🔙 Назад к списку", callback_data="configure_bots")
        ]
    ])


def get_delete_bot_keyboard(bot_id: int):
    """Клавиатура для удаления бота"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="▶️ Запустить", callback_data=f"start_bot_{bot_id}"),
            InlineKeyboardButton(text="⏹️ Остановить", callback_data=f"stop_bot_{bot_id}")
        ],
        # [
        #     InlineKeyboardButton(text="🗑️ Удалить бот", callback_data=f"confirm_delete_{bot_id}")
        # ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="delete_bot")
        ]
    ])

async def get_channels_list_keyboard(bot_id: int, user_id: int):
    """Клавиатура со списком каналов"""
    from database import get_bot_channels
    
    channels = await get_bot_channels(bot_id, user_id)
    
    keyboard = []
    for channel in channels:
        channel_id, channel_link, description, is_active = channel
        status = "🟢" if is_active else "🔴"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{status} {description}", 
                callback_data=f"channel_{channel_id}"
            )
        ])
    
    keyboard.extend([
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data=f"add_channel_{bot_id}")],
        [InlineKeyboardButton(text="🔙 Назад к боту", callback_data=f"bot_{bot_id}")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_channel_management_keyboard(channel_id: int, bot_id: int, is_active: bool):
    """Клавиатура управления каналом"""
    if is_active:
        status_button = InlineKeyboardButton(
            text="⏸️ Деактивировать", 
            callback_data=f"deactivate_channel_{channel_id}"
        )
    else:
        status_button = InlineKeyboardButton(
            text="▶️ Активировать", 
            callback_data=f"activate_channel_{channel_id}"
        )
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [status_button],
        [InlineKeyboardButton(text="✏️ Изменить описание", callback_data=f"edit_channel_desc_{channel_id}")],
        # [InlineKeyboardButton(text="🗑️ Удалить канал", callback_data=f"delete_channel_{channel_id}")],
        [InlineKeyboardButton(text="🔙 Назад к каналам", callback_data=f"list_channels_{bot_id}")]
    ])

def get_back_to_bot_keyboard(bot_id: int):
    """Клавиатура возврата к настройкам бота"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к боту", callback_data=f"bot_{bot_id}")]
    ])

def get_back_to_channels_keyboard(bot_id: int):
    """Клавиатура возврата к списку каналов"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад к каналам", callback_data=f"list_channels_{bot_id}")]
    ])

def get_back_keyboard():
    """Простая клавиатура с кнопкой назад"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

# ===== ПЛАТЕЖНЫЕ КЛАВИАТУРЫ =====

def get_payment_keyboard():
    """Клавиатура выбора тарифа"""
    keyboard = [
        [InlineKeyboardButton(text="🤖 10 каналов - 500 руб", callback_data="buy_bot_1")],
        [InlineKeyboardButton(text="🤖 20 каналов - 900 руб", callback_data="buy_bot_2")],
        [InlineKeyboardButton(text="🤖 50 каналов - 1 700 руб", callback_data="buy_bot_3")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_confirmation_keyboard(payment_id: int, payment_url: str):
    """Клавиатура подтверждения оплаты"""
    keyboard = [
        [InlineKeyboardButton(text="💳 Перейти к оплате", url=payment_url)],
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_payment_{payment_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_payment_{payment_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_success_keyboard():
    """Клавиатура успешной оплаты"""
    keyboard = [
        [InlineKeyboardButton(text="✅ Готово", callback_data="main_menu")],
        [InlineKeyboardButton(text="🛒 Купить еще", callback_data="buy_bots")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_payment_retry_keyboard():
    """Клавиатура при ошибке оплаты"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="buy_bots")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main")]
    ])

def get_payment_pending_keyboard(payment_id: int):
    """Клавиатура при ожидании оплаты"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"check_payment_{payment_id}")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_payment_{payment_id}")]
    ])

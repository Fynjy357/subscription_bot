"""
main_bot/states.py
Состояния FSM для основного бота
"""

from aiogram.fsm.state import State, StatesGroup

class BotStates(StatesGroup):
    """Состояния для управления ботами"""
    waiting_for_token = State()
    waiting_for_message = State()
    waiting_for_channel = State()
    waiting_for_channel_name = State()
    waiting_for_new_channel_name = State()

class EditBotMessage(StatesGroup):
    """Состояния для редактирования сообщений"""
    waiting_for_message = State()

class EditBotButton(StatesGroup):
    """Состояния для редактирования кнопок"""
    waiting_for_button = State()

class EditBotFile(StatesGroup):
    """Состояния для редактирования файлов"""
    waiting_for_file = State()

class AttachImage(StatesGroup):
    """Состояния для прикрепления изображения"""
    waiting_for_image = State()

class MaterialDateManagement(StatesGroup):
    waiting_for_custom_date = State()

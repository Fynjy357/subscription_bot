"""
main_bot/handlers/start.py
Обработчики команды /start и главного меню
"""

import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from database import create_or_update_user, get_user_bots_count, is_super_admin, get_user_total_groups_count, get_user_bot_limit
from ..keyboards import get_main_user_keyboard

async def setup_start_handlers(router: Router):
    """Настройка обработчиков старта и главного меню"""
    
    @router.message(CommandStart())
    async def cmd_start(message: Message):
        """Обработчик команды /start"""
        # Создаем или обновляем пользователя
        await create_or_update_user(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name or ""
        )
        
        # Получаем информацию о лимитах
        bots_count = await get_user_bots_count(message.from_user.id)
        total_groups = await get_user_total_groups_count(message.from_user.id)
        group_limit = await get_user_bot_limit(message.from_user.id)
        
        # Вычисляем сколько каналов можно добавить
        available_channels = group_limit - total_groups
        
        welcome_text = "👋 <b>Главное меню</b>\n\n"
        
        # Добавляем приветствие для супер-админов
        if await is_super_admin(message.from_user.id):
            welcome_text += "⚡ Вы супер-администратор\n\n"
        
        welcome_text += "📊 <b>Ваши лимиты:</b>\n"
        
        # Определяем текст для ботов
        if await is_super_admin(message.from_user.id):
            welcome_text += "🤖 Ботов: безлимитно\n"
        else:
            welcome_text += f"🤖 Ботов: {bots_count} (безлимитно)\n"
        
        # Текст для групп - показываем сколько можно добавить
        welcome_text += f"📢 Вы можете добавить еще {available_channels} каналов\n\n"
        
        welcome_text += "Создавайте и управляйте ботами для проверки подписок на каналы:"
        
        await message.answer(
            welcome_text,
            reply_markup=await get_main_user_keyboard(message.from_user.id),
            parse_mode="HTML"
        )

    @router.callback_query(F.data == "back_to_main")
    async def back_to_main(callback: CallbackQuery):
        """Возврат в главное меню"""
        # Получаем актуальную информацию о лимитах
        bots_count = await get_user_bots_count(callback.from_user.id)
        total_groups = await get_user_total_groups_count(callback.from_user.id)
        group_limit = await get_user_bot_limit(callback.from_user.id)
        
        # Вычисляем сколько каналов можно добавить
        available_channels = group_limit - total_groups
        
        welcome_text = "👋 <b>Главное меню</b>\n\n"
        
        if await is_super_admin(callback.from_user.id):
            welcome_text += "⚡ Вы супер-администратор\n\n"
        
        welcome_text += "📊 <b>Ваши лимиты:</b>\n"
        
        # Определяем текст для ботов
        if await is_super_admin(callback.from_user.id):
            welcome_text += "🤖 Ботов: безлимитно\n"
        else:
            welcome_text += f"🤖 Ботов: {bots_count} (безлимитно)\n"
        
        # Текст для групп - показываем сколько можно добавить
        welcome_text += f"📢 Вы можете добавить еще {available_channels} каналов\n\n"
        
        welcome_text += "Создавайте и управляйте ботами для проверки подписок на каналы:"
        
        await callback.message.edit_text(
            welcome_text,
            reply_markup=await get_main_user_keyboard(callback.from_user.id),
            parse_mode="HTML"
        )

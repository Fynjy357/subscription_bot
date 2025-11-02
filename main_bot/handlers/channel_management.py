"""
main_bot/handlers/channel_management.py
Обработчики управления каналами бота
"""

import asyncio
import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import (
    get_bot_channels, add_channel_to_bot, get_channel_by_id,
    toggle_channel_status, update_channel_description, delete_channel,
    get_bot_by_id, get_bot_token_by_id
)
from worker_bot import start_worker_bot
from ..states import BotStates
from ..keyboards import (
    get_channels_list_keyboard, get_channel_management_keyboard,
    get_back_to_bot_keyboard, get_back_to_channels_keyboard
)

async def setup_channel_management_handlers(router: Router):
    """Настройка обработчиков управления каналами"""
    
    @router.callback_query(F.data.startswith("list_channels_"))
    async def list_channels(callback: CallbackQuery):
        """Показывает список каналов бота"""
        bot_id = int(callback.data.split("_")[2])
        
        # Получаем все каналы бота
        channels = await get_bot_channels(bot_id, callback.from_user.id)
        
        if not channels:
            await callback.message.edit_text(
                f"🤖 <b>Бот:</b> EGE (@egeTOP100_bot)\n\n"
                f"📋 <b>Список каналов:</b>\n\n"
                f"❌ Каналы не добавлены\n\n"
                f"💡 Чтобы добавить канал, нажмите кнопку ниже:",
                reply_markup=await get_channels_list_keyboard(bot_id, callback.from_user.id)
            )
            return
        
        # Формируем текст со списком каналов
        channels_text = "\n".join([f"• {description} (<code>{channel_link}</code>)" for channel_id, channel_link, description, is_active in channels])
        
        await callback.message.edit_text(
            f"🤖 <b>Бот:</b> EGE (@egeTOP100_bot)\n\n"
            f"📋 <b>Список каналов:</b>\n\n"
            f"{channels_text}\n\n"
            f"💡 Выберите канал для редактирования:",
            reply_markup=await get_channels_list_keyboard(bot_id, callback.from_user.id)
        )

    @router.callback_query(F.data.startswith("channel_"))
    async def channel_settings(callback: CallbackQuery):
        """Настройки конкретного канала"""
        try:
            # Безопасный парсинг callback данных
            parts = callback.data.split("_")
            if len(parts) < 2:
                await callback.answer("❌ Ошибка: неверный формат данных", show_alert=True)
                return
            
            # Проверяем, что второй элемент - число
            channel_id_str = parts[1]
            if not channel_id_str.isdigit():
                await callback.answer("❌ Ошибка: неверный ID канала", show_alert=True)
                return
                
            channel_id = int(channel_id_str)
            
            channel = await get_channel_by_id(channel_id, callback.from_user.id)
            
            if not channel:
                await callback.answer("❌ Канал не найден", show_alert=True)
                return
            
            channel_id, channel_link, description, is_active, bot_id, bot_name = channel
            
            status_text = "🟢 Активен" if is_active else "🔴 Неактивен"
            
            await callback.message.edit_text(
                f"⚙️ <b>Настройка канала</b>\n\n"
                f"📢 Канал: <code>{channel_link}</code>\n"
                f"📝 Описание: {description}\n"
                f"📊 Статус: {status_text}\n\n"
                f"Выберите действие:",
                reply_markup=get_channel_management_keyboard(channel_id, bot_id, is_active)
            )
            
        except Exception as e:
            logging.error(f"❌ Ошибка в channel_settings: {e}")
            await callback.answer("❌ Произошла ошибка", show_alert=True)

    async def refresh_channel_settings(callback: CallbackQuery, channel_id: int):
        """Обновляет настройки канала с актуальными данными из БД"""
        try:
            channel = await get_channel_by_id(channel_id, callback.from_user.id)
            
            if not channel:
                await callback.answer("❌ Канал не найден", show_alert=True)
                return
            
            channel_id, channel_link, description, is_active, bot_id, bot_name = channel
            
            status_text = "🟢 Активен" if is_active else "🔴 Неактивен"
            
            await callback.message.edit_text(
                f"⚙️ <b>Настройка канала</b>\n\n"
                f"📢 Канал: <code>{channel_link}</code>\n"
                f"📝 Описание: {description}\n"
                f"📊 Статус: {status_text}\n\n"
                f"Выберите действие:",
                reply_markup=get_channel_management_keyboard(channel_id, bot_id, is_active)
            )
            
        except Exception as e:
            logging.error(f"❌ Ошибка в refresh_channel_settings: {e}")
            await callback.answer("❌ Произошла ошибка при обновлении", show_alert=True)
            
    @router.callback_query(F.data.startswith("add_channel_"))
    async def add_channel_start(callback: CallbackQuery, state: FSMContext):
        """Начало добавления канала"""
        bot_id = int(callback.data.split("_")[2])
        await state.update_data(bot_id=bot_id)
        
        await callback.message.edit_text(
            "➕ <b>Добавление канала</b>\n\n"
            "Пришлите username канала или его ID в формате:\n"
            "<code>@username_channel</code>\nили\n"
            "<code>-1001234567890</code>",
            reply_markup=get_back_to_bot_keyboard(bot_id)
        )
        await state.set_state(BotStates.waiting_for_channel)

    @router.message(BotStates.waiting_for_channel)
    async def process_channel(message: Message, state: FSMContext):
        """Обработка username/ID канала"""
        data = await state.get_data()
        bot_id = data.get('bot_id')
        channel_link = message.text.strip()
        
        # Сохраняем канал и переходим к вводу описания
        await state.update_data(channel_link=channel_link)
        
        await message.answer(
            "📝 <b>Теперь введите описание для этого канала:</b>\n\n"
            "Пример: <i>Мой основной канал</i>\n"
            "Это описание будет отображаться пользователям при проверке подписки.",
            reply_markup=get_back_to_bot_keyboard(bot_id)
        )
        await state.set_state(BotStates.waiting_for_channel_name)

    @router.message(BotStates.waiting_for_channel_name)
    async def process_channel_name(message: Message, state: FSMContext):
        """Обработка описания канала"""
        data = await state.get_data()
        bot_id = data.get('bot_id')
        channel_link = data.get('channel_link')
        description = message.text.strip()
        
        # Добавляем канал в базу данных с передачей telegram_id
        success, result_message = await add_channel_to_bot(bot_id, channel_link, description, message.from_user.id)
        
        if not success:
            await message.answer(
                result_message,
                reply_markup=get_back_to_bot_keyboard(bot_id)
            )
            await state.clear()
            return
        
        # Перезапускаем бота с новыми каналами
        # ВМЕСТО полной распаковки данных бота используем только токен
        bot_token = await get_bot_token_by_id(bot_id)
        if bot_token:
            asyncio.create_task(start_worker_bot(bot_token, bot_id))
        
        # Получаем актуальную информацию о лимите
        from database import get_user_total_groups_count, get_user_bot_limit
        total_groups = await get_user_total_groups_count(message.from_user.id)
        group_limit = await get_user_bot_limit(message.from_user.id)
        
        # Вычисляем сколько каналов можно добавить
        available_channels = group_limit - total_groups
        
        await message.answer(
            f"✅ Канал <code>{channel_link}</code> успешно добавлен!\n"
            f"📝 Описание: {description}\n\n"
            f"📊 Вы можете добавить еще {available_channels} каналов",
            reply_markup=get_back_to_bot_keyboard(bot_id)
        )
        
        await state.clear()

    @router.callback_query(F.data.startswith("activate_channel_"))
    async def activate_channel(callback: CallbackQuery):
        """Активация канала"""
        channel_id = int(callback.data.split("_")[2])
        
        channel = await get_channel_by_id(channel_id, callback.from_user.id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return
        
        await toggle_channel_status(channel_id, callback.from_user.id, True)
        
        # Перезапускаем бота с обновленными каналами
        # ВМЕСТО полной распаковки данных бота используем только токен
        channel_id, channel_link, description, is_active, bot_id, bot_name = channel
        bot_token = await get_bot_token_by_id(bot_id)
        if bot_token:
            asyncio.create_task(start_worker_bot(bot_token, bot_id))
        
        await callback.answer("✅ Канал активирован", show_alert=True)
        # ИСПРАВЛЕНИЕ: Используем refresh_channel_settings вместо channel_settings
        await refresh_channel_settings(callback, channel_id)

    @router.callback_query(F.data.startswith("deactivate_channel_"))
    async def deactivate_channel(callback: CallbackQuery):
        """Деактивация канала"""
        channel_id = int(callback.data.split("_")[2])
        
        channel = await get_channel_by_id(channel_id, callback.from_user.id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return
        
        await toggle_channel_status(channel_id, callback.from_user.id, False)
        
        # Перезапускаем бота с обновленными каналами
        # ВМЕСТО полной распаковки данных бота используем только токен
        channel_id, channel_link, description, is_active, bot_id, bot_name = channel
        bot_token = await get_bot_token_by_id(bot_id)
        if bot_token:
            asyncio.create_task(start_worker_bot(bot_token, bot_id))
        
        await callback.answer("✅ Канал деактивирован", show_alert=True)
        # ИСПРАВЛЕНИЕ: Используем refresh_channel_settings вместо channel_settings
        await refresh_channel_settings(callback, channel_id)

    @router.callback_query(F.data.startswith("edit_channel_desc_"))
    async def edit_channel_description_start(callback: CallbackQuery, state: FSMContext):
        """Начало редактирования описания канала"""
        channel_id = int(callback.data.split("_")[3])
        
        channel = await get_channel_by_id(channel_id, callback.from_user.id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return
        
        channel_id, channel_link, description, is_active, bot_id, bot_name = channel
        
        await state.update_data(channel_id=channel_id, bot_id=bot_id)
        
        await callback.message.edit_text(
            f"✏️ <b>Редактирование описания канала</b>\n\n"
            f"📢 Канал: <code>{channel_link}</code>\n"
            f"📝 Текущее описание: {description}\n\n"
            f"Введите новое описание:",
            reply_markup=get_back_to_channels_keyboard(bot_id)
        )
        await state.set_state(BotStates.waiting_for_new_channel_name)

    @router.message(BotStates.waiting_for_new_channel_name)
    async def process_new_channel_description(message: Message, state: FSMContext):
        """Обработка нового описания канала"""
        data = await state.get_data()
        channel_id = data.get('channel_id')
        bot_id = data.get('bot_id')
        new_description = message.text.strip()
        
        await update_channel_description(channel_id, message.from_user.id, new_description)
        
        # Перезапускаем бота с обновленными каналами
        # ВМЕСТО полной распаковки данных бота используем только токен
        bot_token = await get_bot_token_by_id(bot_id)
        if bot_token:
            asyncio.create_task(start_worker_bot(bot_token, bot_id))
        
        await message.answer(
            f"✅ Описание канала успешно обновлено!\n"
            f"📝 Новое описание: {new_description}",
            reply_markup=get_back_to_channels_keyboard(bot_id)
        )
        
        await state.clear()

    @router.callback_query(F.data.startswith("delete_channel_"))
    async def delete_channel_handler(callback: CallbackQuery):
        """Удаление канала"""
        channel_id = int(callback.data.split("_")[2])
        
        channel = await get_channel_by_id(channel_id, callback.from_user.id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return
        
        channel_id, channel_link, description, is_active, bot_id, bot_name = channel
        
        await delete_channel(channel_id, callback.from_user.id)
        
        # Перезапускаем бота с обновленными каналами
        # ВМЕСТО полной распаковки данных бота используем только токен
        bot_token = await get_bot_token_by_id(bot_id)
        if bot_token:
            asyncio.create_task(start_worker_bot(bot_token, bot_id))
        
        await callback.answer("✅ Канал удален", show_alert=True)
        
        # Возвращаемся к списку каналов
        await list_channels(callback)

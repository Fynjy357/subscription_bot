"""
main_bot/handlers/material_date_management.py
Обработчики управления датой рассылки материала
"""

import logging
from datetime import datetime
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import (
    get_bot_by_id, update_material_sent_date_custom, get_material_sent_date,
    clear_material_sent_date
)
from ..states import MaterialDateManagement
from ..keyboards import get_back_to_bot_keyboard

async def setup_material_date_handlers(router: Router):
    """Настройка обработчиков управления датой рассылки материала"""
    
    @router.callback_query(F.data.startswith("material_date_"))
    async def material_date_menu(callback: CallbackQuery, state: FSMContext):
        """Начало установки даты рассылки материала"""
        bot_id = int(callback.data.replace("material_date_", ""))
        
        # Проверяем права доступа
        bot = await get_bot_by_id(bot_id, callback.from_user.id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return
        
        await state.update_data(material_date_bot_id=bot_id)
        
        # Получаем текущую дату рассылки
        sent_date = await get_material_sent_date(bot_id)
        
        # Распаковываем все 11 значений (добавлено material_sent_at)
        bot_id, bot_token, bot_username, bot_name, is_active, bot_message, button_url, file_id, file_type, image_filename, material_sent_at = bot
        
        if sent_date:
            try:
                date_obj = datetime.fromisoformat(sent_date)
                formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
                current_date_info = f"\n📅 Текущая дата: {formatted_date}"
            except:
                current_date_info = f"\n📅 Текущая дата: {sent_date}"
        else:
            current_date_info = "\n📅 Дата рассылки: ❌ Не установлена"
        
        await callback.message.answer(
            f"📅 <b>Установка даты рассылки материала</b>\n\n"
            f"🤖 Бот: {bot_name} (@{bot_username}){current_date_info}\n\n"
            f"Введите новую дату и время в формате:\n"
            f"<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
            f"<b>Примеры:</b>\n"
            f"• <code>25.12.2024 14:30</code>\n"
            f"• <code>01.01.2025 09:00</code>\n\n"
            f"<i>Чтобы очистить дату, отправьте \"-\"</i>",
            reply_markup=get_back_to_bot_keyboard(bot_id),
            parse_mode="HTML"
        )
        
        await state.set_state(MaterialDateManagement.waiting_for_custom_date)
        await callback.answer()


    @router.message(MaterialDateManagement.waiting_for_custom_date)
    async def process_custom_material_date(message: Message, state: FSMContext):
        """Обработка новой даты рассылки"""
        custom_date = message.text.strip()
        data = await state.get_data()
        bot_id = data.get('material_date_bot_id')
        
        try:
            # Если пользователь хочет очистить дату
            if custom_date.lower() == '-':
                await clear_material_sent_date(bot_id, message.from_user.id)
                
                await message.answer(
                    "✅ <b>Дата рассылки очищена!</b>\n\n"
                    "Материал теперь считается неотправленным.",
                    reply_markup=get_back_to_bot_keyboard(bot_id),
                    parse_mode="HTML"
                )
                
            else:
                # Парсим дату
                date_obj = datetime.strptime(custom_date, "%d.%m.%Y %H:%M")
                
                # Обновляем дату в базе
                await update_material_sent_date_custom(bot_id, message.from_user.id, date_obj)
                
                formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
                
                await message.answer(
                    f"✅ <b>Дата рассылки установлена!</b>\n\n"
                    f"📅 Новая дата: {formatted_date}\n\n"
                    f"Материал считается отправленным в указанное время.",
                    reply_markup=get_back_to_bot_keyboard(bot_id),
                    parse_mode="HTML"
                )
                
        except ValueError:
            await message.answer(
                "❌ <b>Неверный формат даты!</b>\n\n"
                "Пожалуйста, введите дату в формате:\n"
                "<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
                "<b>Примеры:</b>\n"
                "• <code>25.12.2024 14:30</code>\n"
                "• <code>01.01.2025 09:00</code>\n\n"
                "<i>Или отправьте \"-\" для очистки даты</i>",
                reply_markup=get_back_to_bot_keyboard(bot_id),
                parse_mode="HTML"
            )
            return
            
        except Exception as e:
            logging.error(f"❌ Ошибка при установке даты рассылки: {e}")
            await message.answer(
                "❌ Произошла ошибка при установке даты.",
                reply_markup=get_back_to_bot_keyboard(bot_id)
            )
        
        await state.clear()

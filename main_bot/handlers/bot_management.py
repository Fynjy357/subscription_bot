"""
main_bot/handlers/bot_management.py
Обработчики управления ботами (добавление, удаление, запуск/остановка)
"""

import logging
import asyncio
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import (
    get_user_bots_count, is_super_admin, add_bot_to_db, 
    get_user_bots, get_bot_by_id, toggle_bot_status, delete_bot
)
from worker_bot import start_worker_bot, stop_worker_bot
from ..states import BotStates
from ..keyboards import (
    get_main_user_keyboard, get_bots_list_keyboard, 
    get_delete_bots_list_keyboard, get_delete_bot_keyboard,
    get_payment_keyboard, get_back_keyboard, get_bot_management_keyboard
)

async def setup_bot_management_handlers(router: Router):
    """Настройка обработчиков управления ботами"""
    
    async def back_to_main(callback: CallbackQuery):
        """Локальная функция возврата в главное меню"""
        from database import is_super_admin
        welcome_text = "👋 <b>Главное меню</b>\n\n"
        
        if await is_super_admin(callback.from_user.id):
            welcome_text += "⚡ <b>Вы супер-администратор</b>\n\n"
        
        welcome_text += "Создавайте и управляйте ботами для проверки подписок на каналы:"
        
        await callback.message.edit_text(
            welcome_text,
            reply_markup=await get_main_user_keyboard(callback.from_user.id)
        )

    @router.callback_query(F.data.startswith("bot_"))
    async def bot_management_menu(callback: CallbackQuery):
        """Меню управления конкретным ботом"""
        bot_id = int(callback.data.split("_")[1])
        
        bot = await get_bot_by_id(bot_id, callback.from_user.id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return
        
        # Распаковываем все 11 значений (добавлено material_sent_at)
        bot_id, bot_token, bot_username, bot_name, is_active, bot_message, button_url, file_id, file_type, image_filename, material_sent_at = bot
        
        status_text = "🟢 Активен" if is_active else "🔴 Остановлен"
        
        # Формируем информацию о боте
        bot_info = (
            f"🤖 <b>Управление ботом:</b> {bot_name}\n"
            f"🔗 @{bot_username}\n"
            f"📊 Статус: {status_text}\n\n"
        )
        
        # Добавляем информацию о изображении
        if image_filename:
            bot_info += "🖼️ Изображение: ✅ Прикреплено\n"
        else:
            bot_info += "🖼️ Изображение: ❌ Не прикреплено\n"
        
        # Добавляем информацию о сообщении
        if bot_message:
            bot_info += f"📝 Сообщение: {bot_message}\n"
        else:
            bot_info += "📝 Сообщение: Не установлено\n"
            
        # Добавляем информацию о ссылке (бывшая кнопка)
        if button_url:
            bot_info += f"🔗 Ссылка: {button_url}\n"
        else:
            bot_info += "🔗 Ссылка: Не установлена\n"
        
        await callback.message.edit_text(
            bot_info,
            reply_markup=get_bot_management_keyboard(bot_id)
        )

    @router.callback_query(F.data == "add_bot")
    async def add_bot_start(callback: CallbackQuery, state: FSMContext):
        """Начало процесса добавления бота"""
        from database import get_user_bots_count, get_user_bot_limit
        
        # Боты теперь безлимитные, убираем проверку лимита
        await callback.message.edit_text(
            "🤖 <b>Добавление нового бота</b>\n\n"
            "Пришлите токен бота в следующем сообщении:\n\n"
            "ℹ️ <i>Как получить токен:</i>\n"
            "1. Напишите @BotFather\n"
            "2. Команда: /newbot\n"
            "3. Придумайте имя бота\n"
            "4. Получите токен",
            reply_markup=get_back_keyboard()
        )
        await state.set_state(BotStates.waiting_for_token)


    @router.message(BotStates.waiting_for_token)
    async def process_bot_token(message: Message, state: FSMContext):
        """Обработка токена бота"""
        from aiogram import Bot
        
        try:
            bot_token = message.text.strip()
            
            # Проверяем токен
            test_bot = Bot(token=bot_token)
            bot_info = await test_bot.get_me()
            bot_username = bot_info.username
            bot_name = bot_info.first_name
            await test_bot.session.close()
            
            # Сохраняем данные бота в состоянии
            await state.update_data(
                bot_token=bot_token,
                bot_username=bot_username,
                bot_name=bot_name
            )
            
            # Запрашиваем кастомное сообщение
            await message.answer(
                f"✅ Бот @{bot_username} найден!\n\n"
                "📝 Теперь вы можете добавить кастомное сообщение в формате HTML, "
                "которое будет показываться пользователям при запуске бота.\n\n"
                "Примеры форматирования:\n"
                "• <b>Жирный текст</b>\n"
                "• <i>Курсив</i>\n"
                "• <a href='https://example.com'>Ссылка</a>\n"
                "• <code>Моноширинный текст</code>\n\n"
                "Если не хотите добавлять сообщение, отправьте \"-\" или \"нет\""
            )
            
            await state.set_state(BotStates.waiting_for_message)
            
        except Exception as e:
            await message.answer(
                f"❌ Неверный токен бота. Пожалуйста, проверьте токен и попробуйте снова.\n\n"
                f"Ошибка: {str(e)}"
            )

    @router.message(BotStates.waiting_for_message)
    async def process_bot_message(message: Message, state: FSMContext):
        """Обработка кастомного сообщения и сохранение бота"""
        user_message = message.text.strip()
        
        # Если пользователь не хочет добавлять сообщение
        if user_message.lower() in ['-', 'нет', 'no', 'skip']:
            user_message = ""
        
        # Получаем данные из состояния
        data = await state.get_data()
        bot_token = data.get('bot_token')
        bot_username = data.get('bot_username')
        bot_name = data.get('bot_name')
        
        try:
            # Добавляем бота в базу с сообщением
            bot_id = await add_bot_to_db(
                bot_token=bot_token,
                bot_username=bot_username,
                bot_name=bot_name,
                telegram_id=message.from_user.id,
                message=user_message
            )
            
            # Запускаем рабочего бота
            asyncio.create_task(start_worker_bot(bot_token, bot_id))
            
            response_text = f"✅ Бот @{bot_username} успешно добавлен!"
            if user_message:
                response_text += f"\n\n📝 Ваше сообщение сохранено и будет показываться пользователям."
            
            await message.answer(
                response_text,
                reply_markup=await get_main_user_keyboard(message.from_user.id)
            )
            
        except Exception as e:
            logging.error(f"❌ Ошибка при добавлении бота: {e}")
            await message.answer(
                "❌ Произошла ошибка при добавлении бота. Попробуйте снова.",
                reply_markup=await get_main_user_keyboard(message.from_user.id)
            )
        
        await state.clear()

    @router.callback_query(F.data == "configure_bots")
    async def configure_bots(callback: CallbackQuery):
        """Меню настройки ботов"""
        bots = await get_user_bots(callback.from_user.id)
        
        if not bots:
            await callback.answer("❌ У вас нет ботов", show_alert=True)
            return
        
        await callback.message.edit_text(
            "⚙️ <b>Настройка ботов</b>\n\n"
            "Выберите бота для управления:",
            reply_markup=await get_bots_list_keyboard(callback.from_user.id)
        )

    @router.callback_query(F.data == "delete_bot")
    async def delete_bot_menu(callback: CallbackQuery):
        """Меню удаления ботов"""
        bots = await get_user_bots(callback.from_user.id)
        
        if not bots:
            await callback.answer("❌ У вас нет ботов", show_alert=True)
            return
        
        await callback.message.edit_text(
            "🗑️ <b>Управление ботами</b>\n\n"
            "Выберите бота для управления:",
            reply_markup=await get_delete_bots_list_keyboard(callback.from_user.id)
        )

    @router.callback_query(F.data.startswith("manage_bot_"))
    async def manage_bot_for_deletion(callback: CallbackQuery):
        """Управление ботом в меню удаления"""
        bot_id = int(callback.data.split("_")[2])
        
        bot = await get_bot_by_id(bot_id, callback.from_user.id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return
        
        # Распаковываем все 10 значений (включая image_file_id)
        bot_id, bot_token, bot_username, bot_name, is_active, bot_message, button_url, file_id, file_type, image_file_id = bot
        
        status_text = "🟢 Активен" if is_active else "🔴 Остановлен"
        
        await callback.message.edit_text(
            f"⚙️ <b>Управление ботом:</b> {bot_name}\n"
            f"🔗 @{bot_username}\n"
            f"📊 Статус: {status_text}\n\n"
            f"Выберите действие:",
            reply_markup=get_delete_bot_keyboard(bot_id)
        )

    @router.callback_query(F.data.startswith("start_bot_"))
    async def start_bot_handler(callback: CallbackQuery):
        """Запуск бота"""
        bot_id = int(callback.data.split("_")[2])
        
        bot = await get_bot_by_id(bot_id, callback.from_user.id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return
        
        await toggle_bot_status(bot_id, callback.from_user.id, True)
        
        # Запускаем бота
        # Распаковываем все 10 значений (включая image_file_id)
        bot_id, bot_token, bot_username, bot_name, is_active, bot_message, button_url, file_id, file_type, image_file_id = bot
        asyncio.create_task(start_worker_bot(bot_token, bot_id))
        
        await callback.answer("✅ Бот запущен", show_alert=True)
        await manage_bot_for_deletion(callback)

    @router.callback_query(F.data.startswith("stop_bot_"))
    async def stop_bot_handler(callback: CallbackQuery):
        """Остановка бота"""
        bot_id = int(callback.data.split("_")[2])
        
        bot = await get_bot_by_id(bot_id, callback.from_user.id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return
        
        await toggle_bot_status(bot_id, callback.from_user.id, False)
        
        # Останавливаем бота
        await stop_worker_bot(bot_id)
        
        await callback.answer("✅ Бот остановлен", show_alert=True)
        await manage_bot_for_deletion(callback)

    @router.callback_query(F.data.startswith("confirm_delete_"))
    async def confirm_delete_bot(callback: CallbackQuery):
        """Подтверждение удаления бота"""
        bot_id = int(callback.data.split("_")[2])
        
        bot = await get_bot_by_id(bot_id, callback.from_user.id)
        if not bot:
            await callback.answer("❌ Бот не найден", show_alert=True)
            return
        
        # Распаковываем все 10 значений (включая image_file_id)
        bot_id, bot_token, bot_username, bot_name, is_active, bot_message, button_url, file_id, file_type, image_file_id = bot
        
        # Останавливаем бота перед удалением
        await stop_worker_bot(bot_id)
        
        # Удаляем бота из базы
        await delete_bot(bot_id, callback.from_user.id)
        
        await callback.answer("✅ Бот удален", show_alert=True)
        
        # Возвращаемся в главное меню
        await back_to_main(callback)

    @router.callback_query(F.data == "buy_bots")
    async def buy_bots(callback: CallbackQuery):
        """Меню покупки ботов"""
        await callback.message.edit_text(
            "💰 <b>Покупка дополнительных ботов</b>\n\n"
            "Выберите тариф:",
            reply_markup=get_payment_keyboard()
        )

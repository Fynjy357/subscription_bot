"""
main_bot/handlers/admin_handlers.py
Обработчики административной панели
"""

import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from database import (
    get_payment_by_id, get_user_bot_limit, update_payment_status, update_user_bot_limit,
    get_user_payments, is_super_admin
)

async def setup_admin_handlers(router: Router):
    """Настройка обработчиков административной панели"""
    
    @router.callback_query(F.data == "admin_panel")
    async def admin_panel(callback: CallbackQuery):
        """Административная панель"""
        if not await is_super_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        await callback.message.edit_text(
            "⚡ <b>Административная панель</b>\n\n"
            "Выберите действие:",
            reply_markup=get_admin_keyboard()
        )

    @router.callback_query(F.data == "admin_payments")
    async def admin_payments(callback: CallbackQuery):
        """Список платежей для подтверждения"""
        if not await is_super_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        # Здесь можно добавить логику для отображения списка платежей
        await callback.message.edit_text(
            "💰 <b>Управление платежами</b>\n\n"
            "Функционал в разработке...",
            reply_markup=get_admin_back_keyboard()
        )

    @router.callback_query(F.data.startswith("confirm_payment_"))
    async def confirm_payment_admin(callback: CallbackQuery):
        """Подтверждение платежа администратором"""
        if not await is_super_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        payment_id = int(callback.data.split("_")[2])
        payment = await get_payment_by_id(payment_id)
        
        if not payment:
            await callback.answer("❌ Платеж не найден", show_alert=True)
            return
        
        payment_id, user_id, amount, bots_count, status, created_at, telegram_id, username = payment
        
        if status == 'completed':
            await callback.answer("✅ Платеж уже подтвержден", show_alert=True)
            return
        
        # Обновляем статус платежа
        await update_payment_status(payment_id, 'completed')
        
        # Обновляем лимит пользователя
        current_limit = await get_user_bot_limit(telegram_id)
        new_limit = current_limit + bots_count
        await update_user_bot_limit(telegram_id, new_limit)
        
        logging.info(f"✅ Платеж {payment_id} подтвержден. "
                    f"Пользователь {telegram_id} получил +{bots_count} ботов. "
                    f"Новый лимит: {new_limit}")
        
        await callback.answer(f"✅ Платеж подтвержден! Пользователь получил +{bots_count} ботов", show_alert=True)
        await admin_payments(callback)

def get_admin_keyboard():
    """Клавиатура административной панели"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Управление платежами", callback_data="admin_payments")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

def get_admin_back_keyboard():
    """Клавиатура возврата в админ-панель"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")]
    ])

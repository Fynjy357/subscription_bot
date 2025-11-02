"""
main_bot/handlers/payment_handlers.py (исправленная версия)
"""

import logging
from aiogram import F, Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import (
    create_payment, get_payment_by_id, get_user_bot_limit, 
    get_user_by_telegram_id, get_user_used_groups_count
)
from payment_config import TARIFFS
from ..keyboards import (
    get_payment_keyboard, 
    get_payment_confirmation_keyboard,
    get_payment_success_keyboard,
    get_payment_retry_keyboard,
    get_payment_pending_keyboard
)

logger = logging.getLogger(__name__)

async def setup_payment_handlers(router: Router, yookassa_service):
    """Настройка обработчиков платежей"""
    
    @router.callback_query(F.data == "buy_bots")
    async def buy_bots_menu(callback: CallbackQuery):
        """Меню покупки дополнительных групп"""
        if not yookassa_service.is_enabled:
            await callback.message.edit_text(
                "❌ <b>Платежная система временно недоступна</b>\n\n"
                "Покупка дополнительных групп временно отключена.\n"
                "Пожалуйста, обратитесь к администратору.",
                reply_markup=get_payment_retry_keyboard()
            )
            return
        
        used_groups = await get_user_used_groups_count(callback.from_user.id)
        group_limit = await get_user_bot_limit(callback.from_user.id)
        
        await callback.message.edit_text(
            f"💰 <b>Покупка дополнительных групп</b>\n\n"
            f"📊 Использовано групп: <b>{used_groups}/{group_limit}</b>\n\n"
            "Выберите тариф для увеличения лимита групп:",
            reply_markup=get_payment_keyboard()
        )

    @router.callback_query(F.data.startswith("buy_bot_"))
    async def select_tariff(callback: CallbackQuery, state: FSMContext):
        """Выбор тарифа и создание платежа"""
        if not yookassa_service.is_enabled:
            await callback.answer("❌ Платежная система недоступна", show_alert=True)
            return
            
        tariff_id = int(callback.data.split("_")[2])
        
        if tariff_id not in TARIFFS:
            await callback.answer("❌ Неверный тариф", show_alert=True)
            return
        
        tariff = TARIFFS[tariff_id]
        
        # Получаем пользователя
        user = await get_user_by_telegram_id(callback.from_user.id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        user_id = user[0]  # ID пользователя в базе
        
        # Создаем запись о платеже
        payment_id = await create_payment(
            user_id=user_id,
            amount=tariff['amount'],
            bots_count=tariff['bots_count']
        )
        
        # Создаем платеж в YooKassa
        payment_result = await yookassa_service.create_payment(
            payment_id=payment_id,
            amount=tariff['amount'],
            description=tariff['description'],
            user_id=callback.from_user.id
        )
        
        if not payment_result.get('success'):
            await callback.message.edit_text(
                "❌ <b>Ошибка создания платежа</b>\n\n"
                "Не удалось сгенерировать ссылку для оплаты.\n"
                "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
                reply_markup=get_payment_retry_keyboard()
            )
            return
        
        await callback.message.edit_text(
            f"💳 <b>Оплата тарифа: {tariff['description']}</b>\n\n"
            f"💰 Сумма: <b>{tariff['amount']} руб.</b>\n"
            f"🤖 Ботов: <b>{tariff['bots_count']}</b>\n\n"
            f"📝 <b>Инструкция по оплате:</b>\n"
            f"1. Нажмите на кнопку <b>💳 Перейти к оплате</b>\n"
            f"2. Оплатите заказ через ЮMoney\n"
            f"3. <b>После успешной оплаты статус обновится автоматически!</b>\n\n"
            f"✅ <i>Вам не нужно нажимать 'Проверить оплату' - система сделает это сама</i>",
            reply_markup=get_payment_confirmation_keyboard(payment_id, payment_result['confirmation_url'])
        )

    @router.callback_query(F.data.startswith("check_payment_"))
    async def check_payment_status(callback: CallbackQuery):
        """Проверка статуса платежа"""
        payment_id = int(callback.data.split("_")[2])
        
        payment = await get_payment_by_id(payment_id)
        if not payment:
            await callback.answer("❌ Платеж не найден", show_alert=True)
            return
        
        status = payment[4]  # status field
        
        if status == 'completed':
            await callback.message.edit_text(
                "✅ <b>Платеж успешно завершен!</b>\n\n"
                "Ваш лимит ботов был увеличен.\n"
                "Теперь вы можете добавить больше ботов.",
                reply_markup=get_payment_success_keyboard()
            )
        elif status == 'pending':
            await callback.answer(
                "⏳ Платеж еще обрабатывается. Подождите немного...", 
                show_alert=True
            )
        else:
            await callback.message.edit_text(
                "❌ <b>Платеж не завершен</b>\n\n"
                "Пожалуйста, попробуйте оплатить еще раз.",
                reply_markup=get_payment_retry_keyboard()
            )

    logger.info("✅ Payment handlers настроены")

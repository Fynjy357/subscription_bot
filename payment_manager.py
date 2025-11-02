# payment_manager.py
import logging
import asyncio
from database import get_pending_payments, get_user_bot_limit, update_payment_status, update_user_bot_limit

class PaymentManager:
    def __init__(self, yookassa_service):
        self.is_running = False
        self.yookassa_service = yookassa_service
    
    async def start_monitoring(self):
        """Запуск мониторинга платежей"""
        self.is_running = True
        logging.info("🔍 Запуск мониторинга платежей...")
        
        while self.is_running:
            try:
                await self.check_pending_payments()
                await asyncio.sleep(60)
            except Exception as e:
                logging.error(f"❌ Ошибка мониторинга платежей: {e}")
                await asyncio.sleep(30)
    
    async def check_pending_payments(self):
        """Проверка ожидающих платежей"""
        try:
            pending_payments = await get_pending_payments()
            
            for payment in pending_payments:
                # Структура из database.py: 8 полей
                # p.id, p.user_id, p.amount, p.bots_count, p.status, p.yoomoney_operation_id,
                # u.telegram_id, u.username
                if len(payment) >= 8:
                    payment_id, user_id, amount, bots_count, status, yoomoney_id, telegram_id, username = payment
                    
                    if yoomoney_id:
                        status_info = await self.yookassa_service.check_payment_status(yoomoney_id)
                        
                        if status_info.get('paid') and status_info.get('status') == 'succeeded':
                            await self.handle_successful_payment(payment_id, user_id, telegram_id, bots_count)
                        elif status_info.get('status') in ['canceled', 'failed']:
                            await update_payment_status(payment_id, 'canceled')
                else:
                    logging.error(f"❌ Неправильная структура платежа: {payment}")
                        
        except Exception as e:
            logging.error(f"❌ Ошибка проверки платежей: {e}")
    
    async def handle_successful_payment(self, payment_id: int, user_id: int, telegram_id: int, bots_count: int):
        """Обработка успешного платежа"""
        try:
            await update_payment_status(payment_id, 'completed')
            
            current_limit = await get_user_bot_limit(telegram_id)
            new_limit = current_limit + bots_count
            await update_user_bot_limit(telegram_id, new_limit)
            
            logging.info(f"✅ Платеж {payment_id} обработан. Пользователь {telegram_id} получил +{bots_count} ботов")
            
        except Exception as e:
            logging.error(f"❌ Ошибка обработки платежа {payment_id}: {e}")
    
    async def stop_monitoring(self):
        """Остановка мониторинга"""
        self.is_running = False
        logging.info("🛑 Мониторинг платежей остановлен")

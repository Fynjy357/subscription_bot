# webhook_server.py
import logging
import json
import asyncio
from aiohttp import web
from database import get_payment_by_id, get_user_bot_limit, update_payment_status, update_user_bot_limit
from config import WEBHOOK_HOST, WEBHOOK_PORT

class WebhookServer:
    def __init__(self):
        self.app = web.Application()
        self.runner = None
        self.site = None
    
    def setup_routes(self):
        """Настраивает маршруты вебхуков"""
        self.app.router.add_post('/webhook/yookassa', self.handle_yookassa_webhook)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/success', self.payment_success_page)
        self.app.router.add_get('/fail', self.payment_fail_page)
        
        logging.info("✅ Маршруты вебхуков настроены")
    
    async def handle_yookassa_webhook(self, request):
        """Обработка вебхуков от YooKassa"""
        try:
            # Получаем JSON данные
            body = await request.text()
            data = json.loads(body)
            
            logging.info(f"📨 Получен вебхук: {data.get('event')}")
            
            event = data.get('event')
            payment_object = data.get('object', {})
            
            if event == 'payment.succeeded':
                payment_id = payment_object.get('id')
                metadata = payment_object.get('metadata', {})
                
                if payment_id and metadata.get('payment_id'):
                    db_payment_id = metadata['payment_id']
                    user_id = metadata.get('user_id') or metadata.get('telegram_id')
                    await self.process_successful_payment(db_payment_id, payment_id, user_id)
            
            return web.json_response({'status': 'ok'})
        
        except json.JSONDecodeError as e:
            logging.error(f"❌ Ошибка декодирования JSON: {e}")
            return web.json_response({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            logging.error(f"❌ Ошибка обработки вебхука: {e}")
            return web.json_response({'status': 'error', 'message': str(e)}, status=500)
    
    async def process_successful_payment(self, db_payment_id: int, yoomoney_payment_id: str, user_id: str):
        """Обработка успешного платежа"""
        try:
            payment = await get_payment_by_id(db_payment_id)
            if not payment:
                logging.error(f"❌ Платеж {db_payment_id} не найден в базе")
                return
            
            # Правильная распаковка полей из запроса (10 полей из database.py)
            if len(payment) >= 10:
                # Структура из database.py: 
                # p.id, p.user_id, p.amount, p.bots_count, p.status, p.yoomoney_operation_id, 
                # p.created_at, p.completed_at, u.telegram_id, u.username
                payment_id, user_db_id, amount, bots_count, status, yoomoney_id, created_at, completed_at, telegram_id, username = payment
                
                logging.info(f"🔍 Найден платеж: ID={payment_id}, статус={status}, user={telegram_id}")
                
                if status == 'completed':
                    logging.info(f"✅ Платеж {db_payment_id} уже обработан")
                    return
                
                # Обновляем статус и сохраняем yoomoney_operation_id
                await update_payment_status(
                    payment_id=db_payment_id, 
                    status='completed',
                    yoomoney_operation_id=yoomoney_payment_id
                )
                
                # Обновляем лимит пользователя
                current_limit = await get_user_bot_limit(telegram_id)
                new_limit = current_limit + bots_count
                await update_user_bot_limit(telegram_id, new_limit)
                
                logging.info(f"✅ Вебхук: Пользователь {telegram_id} получил +{bots_count} ботов. Новый лимит: {new_limit}")
                
                # Отправляем уведомление пользователю
                await self.send_payment_notification(telegram_id, bots_count, amount)
            else:
                logging.error(f"❌ Неправильная структура платежа: {payment}")
                
        except Exception as e:
            logging.error(f"❌ Ошибка обработки успешного платежа: {e}")
            logging.error(f"🔍 Структура платежа: {payment}")
    
    async def send_payment_notification(self, telegram_id: int, bots_count: int, amount: float):
        """Отправка уведомления пользователю"""
        try:
            # Используем новую функцию get_main_bot()
            from main_bot.bot_manager import get_main_bot
            
            main_bot = get_main_bot()
            if not main_bot:
                logging.warning(f"⚠️ Бот не запущен, уведомление не отправлено пользователю {telegram_id}")
                return
            
            message = (
                f"🎉 Оплата прошла успешно!\n\n"
                f"💳 Сумма: {amount} руб\n"
                f"🤖 Получено ботов: +{bots_count}\n\n"
                f"Теперь вы можете создать новых ботов в меню управления."
            )
            
            await main_bot.send_message(telegram_id, message)
            logging.info(f"📢 Уведомление отправлено пользователю {telegram_id}")
            
        except Exception as e:
            logging.error(f"❌ Ошибка отправки уведомления: {e}")
    
    async def health_check(self, request):
        """Проверка здоровья сервера"""
        return web.json_response({
            "status": "healthy",
            "service": "webhook_server",
            "host": WEBHOOK_HOST,
            "port": WEBHOOK_PORT,
            "endpoints": {
                "yookassa_webhook": f"http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/webhook/yookassa",
                "health": f"http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/health"
            }
        })
    
    async def payment_success_page(self, request):
        return web.json_response({
            "status": "success",
            "message": "Оплата прошла успешно! Вернитесь в бота для проверки статуса."
        })
    
    async def payment_fail_page(self, request):
        return web.json_response({
            "status": "fail", 
            "message": "Оплата не прошла. Попробуйте снова."
        })
    
    async def start(self):
        """Запускает вебхук сервер"""
        self.setup_routes()
        
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, '0.0.0.0', WEBHOOK_PORT)
        await self.site.start()
        
        logging.info(f"🚀 Webhook сервер запущен на {WEBHOOK_HOST}:{WEBHOOK_PORT}")
        logging.info(f"🌐 YooKassa webhook: http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/webhook/yookassa")
        logging.info(f"❤️ Health check: http://{WEBHOOK_HOST}:{WEBHOOK_PORT}/health")
        
        return self.runner
    
    async def stop(self):
        """Останавливает вебхук сервер"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logging.info("✅ Вебхук сервер остановлен")

# Глобальный экземпляр
webhook_server = WebhookServer()

# Функции для обратной совместимости
async def start_webhook_server():
    return await webhook_server.start()

def create_webhook_app():
    server = WebhookServer()
    server.setup_routes()
    return server.app

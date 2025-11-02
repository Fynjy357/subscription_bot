# yookassa_service.py
import uuid
import logging
from yookassa import Configuration, Payment

class YooKassaService:
    def __init__(self, shop_id: str, secret_key: str):
        self.is_enabled = bool(shop_id and secret_key and shop_id != 'test_shop_id')
        
        if self.is_enabled:
            Configuration.account_id = shop_id
            Configuration.secret_key = secret_key
            logging.info("✅ YooKassa сервис инициализирован")
        else:
            logging.warning("⚠️ YooKassa в тестовом режиме")

    async def create_payment(self, payment_id: int, amount: float, description: str, user_id: int):
        """Создание платежа в YooKassa"""
        try:
            if not self.is_enabled:
                return {
                    'success': True,
                    'confirmation_url': f"https://yoomoney.ru/checkout/payments/v2/contract?orderId=test_{payment_id}",
                    'payment_id': f"test_{payment_id}"
                }

            idempotence_key = str(uuid.uuid4())
            
            payment = Payment.create({
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": f"https://t.me/your_bot?start=payment_{payment_id}"
                },
                "capture": True,
                "description": f"{description} (Payment #{payment_id})",
                "metadata": {
                    "payment_id": payment_id,
                    "user_id": user_id
                }
            }, idempotence_key)

            return {
                'success': True,
                'confirmation_url': payment.confirmation.confirmation_url,
                'payment_id': payment.id
            }
        except Exception as e:
            logging.error(f"❌ Ошибка создания платежа: {e}")
            return {'success': False, 'error': str(e)}

    async def check_payment_status(self, payment_id: str):
        """Проверка статуса платежа"""
        try:
            if not self.is_enabled or payment_id.startswith('test_'):
                return {'status': 'succeeded', 'paid': True}

            payment = Payment.find_one(payment_id)
            return {
                'status': payment.status,
                'paid': payment.paid
            }
        except Exception as e:
            logging.error(f"❌ Ошибка проверки статуса платежа: {e}")
            return {'status': 'unknown', 'paid': False}

# worker_bot/main_bot_client.py
import logging
from aiogram import Bot
from aiogram.enums import ChatMemberStatus

class MainBotClient:
    def __init__(self, token: str):
        self.bot = Bot(token=token)
        self.bot_info = None
    
    async def initialize(self):
        """Инициализация основного бота"""
        self.bot_info = await self.bot.get_me()
        logging.info(f"✅ Основной бот @{self.bot_info.username} инициализирован")
    
    async def check_user_subscription(self, user_id: int, channel: str) -> bool:
        """Проверка подписки на канал"""
        try:
            channel_clean = channel.lstrip('@')
            
            # Для публичных каналов пробуем получить статус пользователя
            chat = await self.bot.get_chat(f"@{channel_clean}")
            
            # Пробуем получить информацию о пользователе в канале
            try:
                member = await self.bot.get_chat_member(chat_id=chat.id, user_id=user_id)
                is_subscribed = member.status not in ['left', 'kicked', 'restricted']
                logging.info(f"📊 Канал {channel}, статус: {member.status}, подписан: {is_subscribed}")
                return is_subscribed
                
            except Exception as member_error:
                error_msg = str(member_error).lower()
                
                # Если бот не является администратором канала
                if "member list is inaccessible" in error_msg or "not enough rights" in error_msg:
                    logging.warning(f"⚠️ Бот не является администратором канала {channel}")
                    # ИЗМЕНЕНИЕ: Если не можем проверить - считаем что НЕ подписан
                    return False
                elif "user not found" in error_msg or "user not participant" in error_msg:
                    logging.info(f"👤 Пользователь {user_id} не найден в канале {channel}")
                    return False
                else:
                    logging.warning(f"⚠️ Неизвестная ошибка проверки {channel}: {error_msg}")
                    return False
                    
        except Exception as e:
            logging.error(f"💥 Общая ошибка при проверке {channel}: {e}")
            return False

    async def close(self):
        """Закрывает сессию основного бота"""
        await self.bot.session.close()

# Глобальный экземпляр основного бота
main_bot_client = None

async def init_main_bot(token: str):
    """Инициализирует основной бот"""
    global main_bot_client
    main_bot_client = MainBotClient(token)
    await main_bot_client.initialize()
    return main_bot_client

def get_main_bot():
    """Возвращает экземпляр основного бота"""
    return main_bot_client
# database.py
import aiosqlite
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def init_db():
    """Инициализация базы данных"""
    try:
        async with aiosqlite.connect('subscription_bot.db') as db:
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    bot_limit INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица ботов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS bots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    bot_token TEXT UNIQUE NOT NULL,
                    bot_username TEXT,
                    bot_name TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    message TEXT DEFAULT '',
                    button_url TEXT DEFAULT '',
                    file_id TEXT DEFAULT '',
                    file_type TEXT DEFAULT '',
                    image_filename TEXT DEFAULT '',
                    material_sent_at TIMESTAMP,  -- НОВОЕ ПОЛЕ: дата рассылки материала
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # Таблица платежей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    bots_count INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending',
                    yoomoney_operation_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # Таблица каналов
            await db.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    bot_id INTEGER NOT NULL,
                    channel_link TEXT NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id),
                    FOREIGN KEY (bot_id) REFERENCES bots (id)
                )
            ''')

            await db.commit()
            logger.info("✅ База данных инициализирована")
            
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации базы данных: {e}")
        raise

# ===== ПОЛЬЗОВАТЕЛИ =====

async def create_or_update_user(telegram_id: int, username: str, first_name: str, last_name: str = ""):
    """Создание или обновление пользователя"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        existing_user = await cursor.fetchone()
        
        if existing_user:
            await db.execute(
                'UPDATE users SET username = ?, first_name = ?, last_name = ? WHERE telegram_id = ?',
                (username, first_name, last_name, telegram_id)
            )
            logging.debug(f"👤 Пользователь {telegram_id} обновлен")
        else:
            cursor = await db.execute(
                'INSERT INTO users (telegram_id, username, first_name, last_name, bot_limit) VALUES (?, ?, ?, ?, ?)',
                (telegram_id, username, first_name, last_name, 10)  # Дефолтный лимит групп = 10
            )
            logging.info(f"✅ Новый пользователь {telegram_id} создан с лимитом 10 групп")
        
        await db.commit()

async def get_user_used_groups_count(telegram_id: int):
    """Получение количества использованных групп пользователем (активные каналы)"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT COUNT(*) 
            FROM channels c
            JOIN bots b ON c.bot_id = b.id
            JOIN users u ON b.user_id = u.id
            WHERE u.telegram_id = ? AND c.is_active = TRUE
        ''', (telegram_id,))
        result = await cursor.fetchone()
        return result[0] if result else 0
    

async def check_group_limit(telegram_id: int):
    """Проверяет, не превышен ли лимит групп"""
    total_groups = await get_user_total_groups_count(telegram_id)
    group_limit = await get_user_bot_limit(telegram_id)
    return total_groups < group_limit, total_groups, group_limit

async def get_user_by_telegram_id(telegram_id: int):
    """Получение пользователя по telegram_id"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT id, username, first_name, last_name, bot_limit
            FROM users 
            WHERE telegram_id = ?
        ''', (telegram_id,))
        user = await cursor.fetchone()
        return user

async def get_user_bot_limit(telegram_id: int):
    """Получение лимита ботов пользователя"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('SELECT bot_limit FROM users WHERE telegram_id = ?', (telegram_id,))
        result = await cursor.fetchone()
        return result[0] if result else 1

async def update_user_bot_limit(telegram_id: int, new_limit: int):
    """Обновление лимита ботов пользователя"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        await db.execute('UPDATE users SET bot_limit = ? WHERE telegram_id = ?', (new_limit, telegram_id))
        await db.commit()
        logging.info(f"📊 Лимит пользователя {telegram_id} обновлен: {new_limit}")

# ===== БОТЫ =====

async def add_bot_to_db(bot_token: str, bot_username: str, bot_name: str, telegram_id: int, message: str = ""):
    """Добавление бота в базу данных"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user_record = await cursor.fetchone()
        
        if not user_record:
            await create_or_update_user(telegram_id, "", "", "")
            cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user_record = await cursor.fetchone()
        
        user_db_id = user_record[0]
        
        cursor = await db.execute("SELECT id FROM bots WHERE bot_token = ?", (bot_token,))
        existing_bot = await cursor.fetchone()
        
        if existing_bot:
            logging.warning(f"⚠️ Бот с токеном уже существует (ID: {existing_bot[0]})")
            return existing_bot[0]
        
        cursor = await db.execute(
            'INSERT INTO bots (bot_token, bot_username, bot_name, user_id, message) VALUES (?, ?, ?, ?, ?)',
            (bot_token, bot_username, bot_name, user_db_id, message)
        )
        await db.commit()
        
        logging.info(f"✅ Бот @{bot_username} добавлен для пользователя {telegram_id}")
        return cursor.lastrowid

async def get_user_bots_count(telegram_id: int):
    """Получение количества ботов пользователя"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT COUNT(*) 
            FROM bots b 
            JOIN users u ON b.user_id = u.id 
            WHERE u.telegram_id = ?
        ''', (telegram_id,))
        result = await cursor.fetchone()
        return result[0] if result else 0

async def get_user_bots(telegram_id: int):
    """Получение всех ботов пользователя"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user_record = await cursor.fetchone()
        
        if not user_record:
            return []
        
        user_db_id = user_record[0]
        
        cursor = await db.execute('''
            SELECT b.id, b.bot_token, b.bot_username, b.bot_name, b.is_active, 
                   b.message, b.button_url, b.file_id, b.file_type, b.image_filename,
                   b.material_sent_at
            FROM bots b 
            WHERE b.user_id = ?
        ''', (user_db_id,))
        bots = await cursor.fetchall()
        return bots

async def get_user_bots_for_keyboard(telegram_id: int):
    """Получение упрощенного списка ботов пользователя для клавиатур"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user_record = await cursor.fetchone()
        
        if not user_record:
            return []
        
        user_db_id = user_record[0]
        
        cursor = await db.execute('''
            SELECT b.id, b.bot_username, b.bot_name, b.is_active
            FROM bots b 
            WHERE b.user_id = ?
        ''', (user_db_id,))
        bots = await cursor.fetchall()
        return bots

async def get_bot_by_id(bot_id: int, telegram_id: int):
    """Получение бота по ID с проверкой владельца"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT b.id, b.bot_token, b.bot_username, b.bot_name, b.is_active, 
                   b.message, b.button_url, b.file_id, b.file_type, b.image_filename,
                   b.material_sent_at
            FROM bots b 
            WHERE b.id = ? AND b.user_id = (SELECT id FROM users WHERE telegram_id = ?)
        ''', (bot_id, telegram_id))
        bot = await cursor.fetchone()
        return bot

async def get_bot_with_media(bot_id: int, telegram_id: int):
    """Получение бота с медиа-данными"""
    return await get_bot_by_id(bot_id, telegram_id)

async def get_bot_token_by_id(bot_id: int):
    """Получение токена бота по ID"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('SELECT bot_token FROM bots WHERE id = ?', (bot_id,))
        result = await cursor.fetchone()
        return result[0] if result else None

async def get_all_active_bots():
    """Получение всех активных ботов для запуска"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT b.id, b.bot_token, b.bot_username, b.bot_name, b.is_active
            FROM bots b 
            WHERE b.is_active = TRUE
        ''')
        bots = await cursor.fetchall()
        return bots

async def toggle_bot_status(bot_id: int, telegram_id: int, is_active: bool):
    """Включение/выключение бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        await db.execute('''
            UPDATE bots 
            SET is_active = ? 
            WHERE id = ? AND user_id = (SELECT id FROM users WHERE telegram_id = ?)
        ''', (is_active, bot_id, telegram_id))
        await db.commit()
        logging.info(f"🔄 Статус бота {bot_id} изменен: {'активен' if is_active else 'неактивен'}")

async def delete_bot(bot_id: int, telegram_id: int):
    """Удаление бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        await db.execute('''
            DELETE FROM bots 
            WHERE id = ? AND user_id = (SELECT id FROM users WHERE telegram_id = ?)
        ''', (bot_id, telegram_id))
        await db.commit()
        logging.info(f"🗑️ Бот {bot_id} удален")

# ===== СООБЩЕНИЯ И МЕДИА =====

async def update_bot_message(bot_id: int, telegram_id: int, message: str):
    """Обновление сообщения бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        await db.execute('''
            UPDATE bots 
            SET message = ? 
            WHERE id = ? AND user_id = (SELECT id FROM users WHERE telegram_id = ?)
        ''', (message, bot_id, telegram_id))
        await db.commit()
        logging.info(f"📝 Сообщение бота {bot_id} обновлено")

async def get_bot_message(bot_id: int):
    """Получение сообщения бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('SELECT message FROM bots WHERE id = ?', (bot_id,))
        result = await cursor.fetchone()
        return result[0] if result and result[0] else ""

async def update_bot_button_url(bot_id: int, telegram_id: int, button_url: str):
    """Обновление ссылки/текста для кнопки бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        await db.execute('''
            UPDATE bots 
            SET button_url = ? 
            WHERE id = ? AND user_id = (SELECT id FROM users WHERE telegram_id = ?)
        ''', (button_url, bot_id, telegram_id))
        await db.commit()
        logging.info(f"🔘 Кнопка бота {bot_id} обновлена")

async def remove_bot_button_url(bot_id: int, telegram_id: int):
    """Удаление ссылки/текста кнопки бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        await db.execute('''
            UPDATE bots 
            SET button_url = '' 
            WHERE id = ? AND user_id = (SELECT id FROM users WHERE telegram_id = ?)
        ''', (bot_id, telegram_id))
        await db.commit()
        logging.info(f"🔘 Кнопка бота {bot_id} удалена")

async def update_bot_file(bot_id: int, telegram_id: int, file_id: str, file_type: str):
    """Обновление файла бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        await db.execute('''
            UPDATE bots 
            SET file_id = ?, file_type = ? 
            WHERE id = ? AND user_id = (SELECT id FROM users WHERE telegram_id = ?)
        ''', (file_id, file_type, bot_id, telegram_id))
        await db.commit()
        logging.info(f"📎 Файл бота {bot_id} обновлен (тип: {file_type})")

async def remove_bot_file(bot_id: int, telegram_id: int):
    """Удаление файла бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        await db.execute('''
            UPDATE bots 
            SET file_id = '', file_type = '' 
            WHERE id = ? AND user_id = (SELECT id FROM users WHERE telegram_id = ?)
        ''', (bot_id, telegram_id))
        await db.commit()
        logging.info(f"📎 Файл бота {bot_id} удален")

# картинка для бота

async def update_bot_image(bot_id: int, telegram_id: int, filename: str):
    """Обновляет изображение бота (имя файла)"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        # Проверяем права доступа
        cursor = await db.execute('''
            SELECT * FROM bots 
            WHERE id = ? AND user_id = (SELECT id FROM users WHERE telegram_id = ?)
        ''', (bot_id, telegram_id))
        bot = await cursor.fetchone()
        
        if not bot:
            raise Exception("Бот не найден или нет прав доступа")
        
        # Обновляем имя файла изображения
        await db.execute(
            "UPDATE bots SET image_filename = ? WHERE id = ?",
            (filename, bot_id)
        )
        await db.commit()
        logging.info(f"🖼️ Изображение бота {bot_id} обновлено: {filename}")

async def remove_bot_image(bot_id: int, telegram_id: int):
    """Удаляет изображение бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        # Проверяем права доступа
        cursor = await db.execute('''
            SELECT * FROM bots 
            WHERE id = ? AND user_id = (SELECT id FROM users WHERE telegram_id = ?)
        ''', (bot_id, telegram_id))
        bot = await cursor.fetchone()
        
        if not bot:
            raise Exception("Бот не найден или нет прав доступа")
        
        # Получаем имя файла для удаления
        cursor = await db.execute('SELECT image_filename FROM bots WHERE id = ?', (bot_id,))
        result = await cursor.fetchone()
        filename = result[0] if result else None
        
        # Удаляем файл из базы
        await db.execute(
            "UPDATE bots SET image_filename = NULL WHERE id = ?",
            (bot_id,)
        )
        await db.commit()
        
        # Удаляем физический файл
        if filename:
            from main_bot.file_utils import delete_bot_image
            delete_bot_image(bot_id, filename)
        
        logging.info(f"🖼️ Изображение бота {bot_id} удалено")

async def get_bot_image_filename(bot_id: int):
    """Получение имени файла изображения бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('SELECT image_filename FROM bots WHERE id = ?', (bot_id,))
        result = await cursor.fetchone()
        return result[0] if result and result[0] else None

# ===== ДАТА РАССЫЛКИ МАТЕРИАЛА =====

async def update_material_sent_date(bot_id: int, telegram_id: int = None):
    """Обновляет дату рассылки материала для бота на текущее время"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        if telegram_id:
            # С проверкой владельца
            await db.execute('''
                UPDATE bots 
                SET material_sent_at = datetime('now') 
                WHERE id = ? AND user_id = (SELECT id FROM users WHERE telegram_id = ?)
            ''', (bot_id, telegram_id))
        else:
            # Без проверки владельца (для рабочих ботов)
            await db.execute('''
                UPDATE bots 
                SET material_sent_at = datetime('now') 
                WHERE id = ?
            ''', (bot_id,))
        
        await db.commit()
        logging.info(f"📅 Дата рассылки материала для бота {bot_id} обновлена")

async def update_material_sent_date_custom(bot_id: int, telegram_id: int, custom_date: datetime):
    """Обновляет дату рассылки материала для бота с кастомной датой"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        await db.execute('''
            UPDATE bots 
            SET material_sent_at = ? 
            WHERE id = ? AND user_id = (SELECT id FROM users WHERE telegram_id = ?)
        ''', (custom_date.isoformat(), bot_id, telegram_id))
        
        await db.commit()
        logging.info(f"📅 Дата рассылки материала для бота {bot_id} установлена: {custom_date}")

async def get_material_sent_date(bot_id: int):
    """Получает дату рассылки материала для бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('SELECT material_sent_at FROM bots WHERE id = ?', (bot_id,))
        result = await cursor.fetchone()
        return result[0] if result else None

async def get_bots_with_material_sent_date():
    """Получает всех ботов с датой рассылки материала"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT b.id, b.bot_username, b.bot_name, b.material_sent_at, 
                   u.telegram_id, u.username
            FROM bots b
            JOIN users u ON b.user_id = u.id
            WHERE b.material_sent_at IS NOT NULL
            ORDER BY b.material_sent_at DESC
        ''')
        bots = await cursor.fetchall()
        return bots

async def clear_material_sent_date(bot_id: int, telegram_id: int = None):
    """Очищает дату рассылки материала для бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        if telegram_id:
            # С проверкой владельца
            await db.execute('''
                UPDATE bots 
                SET material_sent_at = NULL 
                WHERE id = ? AND user_id = (SELECT id FROM users WHERE telegram_id = ?)
            ''', (bot_id, telegram_id))
        else:
            # Без проверки владельца
            await db.execute('''
                UPDATE bots 
                SET material_sent_at = NULL 
                WHERE id = ?
            ''', (bot_id,))
        
        await db.commit()
        logging.info(f"📅 Дата рассылки материала для бота {bot_id} очищена")

# ===== КАНАЛЫ =====

async def add_channel_to_bot(bot_id: int, channel_link: str, description: str, telegram_id: int = None):
    """Добавление канала к боту с валидацией формата и проверкой лимита"""
    validated_link = validate_channel_link(channel_link)
    
    if await check_channel_exists(bot_id, validated_link):
        logging.warning(f"⚠️ Канал {validated_link} уже существует у бота {bot_id}")
        return False, "Канал уже существует у этого бота"
    
    # Получаем user_id из telegram_id
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('SELECT id FROM users WHERE telegram_id = ?', (telegram_id,))
        user_record = await cursor.fetchone()
        if not user_record:
            raise ValueError(f"Пользователь с telegram_id {telegram_id} не найден")
        
        user_id = user_record[0]
        
        # Проверяем лимит групп
        can_add, total_groups, group_limit = await check_group_limit(telegram_id)
        if not can_add:
            return False, f"❌ Достигнут лимит групп!\n\nВы можете добавить еще 0 каналов\n\nЧтобы добавить больше каналов, приобретите один из тарифов."
    
    # Если лимит не превышен, добавляем канал
    async with aiosqlite.connect('subscription_bot.db') as db:
        await db.execute(
            'INSERT INTO channels (bot_id, channel_link, description, user_id, is_active) VALUES (?, ?, ?, ?, ?)',
            (bot_id, validated_link, description, user_id, True)
        )
        await db.commit()
        
        logging.info(f"✅ Канал добавлен: {channel_link} -> {validated_link}")
        return True, "Канал успешно добавлен"


async def get_bot_channels(bot_id: int, telegram_id: int, only_active: bool = False):
    """Получение каналов бота с проверкой владельца"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        query = '''
            SELECT c.id, c.channel_link, c.description, c.is_active
            FROM channels c
            JOIN bots b ON c.bot_id = b.id
            WHERE c.bot_id = ? AND b.user_id = (SELECT id FROM users WHERE telegram_id = ?)
        '''
        if only_active:
            query += ' AND c.is_active = TRUE'
        
        cursor = await db.execute(query, (bot_id, telegram_id))
        channels = await cursor.fetchall()
        return channels
    
async def get_user_total_groups_count(telegram_id: int):
    """Получение общего количества групп пользователя (включая неактивные)"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT COUNT(*) 
            FROM channels c
            JOIN bots b ON c.bot_id = b.id
            JOIN users u ON b.user_id = u.id
            WHERE u.telegram_id = ?
        ''', (telegram_id,))
        result = await cursor.fetchone()
        return result[0] if result else 0
    
    
async def get_bot_channels_for_worker(bot_id: int):
    """Получение каналов бота для рабочих ботов (без проверки владельца)"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT id, channel_link, description, is_active
            FROM channels
            WHERE bot_id = ? AND is_active = TRUE
        ''', (bot_id,))
        channels = await cursor.fetchall()
        return channels

async def get_active_bot_channels(bot_id: int):
    """Получение активных каналов бота"""
    return await get_bot_channels_for_worker(bot_id)

async def get_channel_by_id(channel_id: int, telegram_id: int):
    """Получение канала по ID с проверкой владельца"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT c.id, c.channel_link, c.description, c.is_active, b.id as bot_id, b.bot_name
            FROM channels c
            JOIN bots b ON c.bot_id = b.id
            WHERE c.id = ? AND b.user_id = (SELECT id FROM users WHERE telegram_id = ?)
        ''', (channel_id, telegram_id))
        channel = await cursor.fetchone()
        return channel

async def toggle_channel_status(channel_id: int, telegram_id: int, is_active: bool):
    """Включение/выключение канала"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        await db.execute('''
            UPDATE channels 
            SET is_active = ? 
            WHERE id = ? AND bot_id IN (
                SELECT b.id FROM bots b 
                WHERE b.user_id = (SELECT id FROM users WHERE telegram_id = ?)
            )
        ''', (is_active, channel_id, telegram_id))
        await db.commit()
        logging.info(f"🔄 Статус канала {channel_id} изменен: {'активен' if is_active else 'неактивен'}")

async def update_channel_description(channel_id: int, telegram_id: int, description: str):
    """Обновление описания канала"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        await db.execute('''
            UPDATE channels 
            SET description = ? 
            WHERE id = ? AND bot_id IN (
                SELECT b.id FROM bots b 
                WHERE b.user_id = (SELECT id FROM users WHERE telegram_id = ?)
            )
        ''', (description, channel_id, telegram_id))
        await db.commit()
        logging.info(f"✏️ Описание канала {channel_id} обновлено")

async def delete_channel(channel_id: int, telegram_id: int):
    """Удаление канала"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        await db.execute('''
            DELETE FROM channels 
            WHERE id = ? AND bot_id IN (
                SELECT b.id FROM bots b 
                WHERE b.user_id = (SELECT id FROM users WHERE telegram_id = ?)
            )
        ''', (channel_id, telegram_id))
        await db.commit()
        logging.info(f"🗑️ Канал {channel_id} удален")

async def get_bot_channels_count(bot_id: int, telegram_id: int, only_active: bool = False):
    """Получение количества каналов бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        query = '''
            SELECT COUNT(*)
            FROM channels c
            JOIN bots b ON c.bot_id = b.id
            WHERE c.bot_id = ? AND b.user_id = (SELECT id FROM users WHERE telegram_id = ?)
        '''
        if only_active:
            query += ' AND c.is_active = TRUE'
        
        cursor = await db.execute(query, (bot_id, telegram_id))
        result = await cursor.fetchone()
        return result[0] if result else 0


async def check_channel_exists(bot_id: int, channel_link: str):
    """Проверка существования канала у бота"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT id FROM channels 
            WHERE bot_id = ? AND channel_link = ?
        ''', (bot_id, channel_link))
        result = await cursor.fetchone()
        return result is not None

# ===== ПЛАТЕЖИ =====

async def create_payment(user_id: int, amount: int, bots_count: int, yoomoney_operation_id: str = None):
    """Создание записи о платеже"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            INSERT INTO payments (user_id, amount, bots_count, status, yoomoney_operation_id) 
            VALUES (?, ?, ?, 'pending', ?)
        ''', (user_id, amount, bots_count, yoomoney_operation_id))
        await db.commit()
        payment_id = cursor.lastrowid
        logging.info(f"💰 Создан платеж {payment_id} для пользователя {user_id}")
        return payment_id

async def get_payment_by_id(payment_id: int):
    """Получение платежа по ID"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT p.id, p.user_id, p.amount, p.bots_count, p.status, p.yoomoney_operation_id, p.created_at, p.completed_at,
                   u.telegram_id, u.username
            FROM payments p
            JOIN users u ON p.user_id = u.id
            WHERE p.id = ?
        ''', (payment_id,))
        payment = await cursor.fetchone()
        return payment

async def get_user_payments(telegram_id: int):
    """Получение платежей пользователя"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT p.id, p.amount, p.bots_count, p.status, p.created_at, p.completed_at
            FROM payments p
            JOIN users u ON p.user_id = u.id
            WHERE u.telegram_id = ?
            ORDER BY p.created_at DESC
        ''', (telegram_id,))
        payments = await cursor.fetchall()
        return payments

async def get_pending_payments():
    """Получение ожидающих платежей"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT p.id, p.user_id, p.amount, p.bots_count, p.status, p.yoomoney_operation_id,
                   u.telegram_id, u.username
            FROM payments p
            JOIN users u ON p.user_id = u.id
            WHERE p.status = 'pending'
            AND p.created_at > datetime('now', '-1 day')
        ''')
        return await cursor.fetchall()

async def update_payment_status(payment_id: int, status: str, yoomoney_operation_id: str = None):
    """Обновление статуса платежа"""
    try:
        conn = await aiosqlite.connect('subscription_bot.db')
        cursor = await conn.cursor()
        
        if yoomoney_operation_id:
            await cursor.execute('''
                UPDATE payments 
                SET status = ?, yoomoney_operation_id = ?, completed_at = datetime('now')
                WHERE id = ?
            ''', (status, yoomoney_operation_id, payment_id))
        else:
            await cursor.execute('''
                UPDATE payments 
                SET status = ?, completed_at = datetime('now')
                WHERE id = ?
            ''', (status, payment_id))
        
        await conn.commit()
        logging.info(f"📊 Платеж {payment_id} обновлен: статус={status}, операция={yoomoney_operation_id}")
        
    except Exception as e:
        logging.error(f"❌ Ошибка обновления платежа {payment_id}: {e}")
        raise
    finally:
        await conn.close()

# ===== АДМИНИСТРАТИВНЫЕ ФУНКЦИИ =====

async def is_super_admin(telegram_id: int):
    """Проверка является ли пользователь супер-администратором"""
    from config import SUPER_ADMIN_IDS
    return telegram_id in SUPER_ADMIN_IDS

async def get_all_channels():
    """Получение всех каналов (для отладки)"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        cursor = await db.execute('''
            SELECT c.id, c.channel_link, c.description, c.is_active, b.bot_name
            FROM channels c
            JOIN bots b ON c.bot_id = b.id
        ''')
        channels = await cursor.fetchall()
        return channels

# ===== ВАЛИДАЦИЯ =====

def validate_channel_link(channel_link: str) -> str:
    """Валидирует и нормализует формат ссылки на канал"""
    if not channel_link:
        return channel_link
    
    channel_link = channel_link.strip()
    
    # Преобразуем в правильный формат @username
    if channel_link.startswith('https://t.me/'):
        return '@' + channel_link.replace('https://t.me/', '')
    elif channel_link.startswith('t.me/'):
        return '@' + channel_link.replace('t.me/', '')
    elif channel_link.startswith('http://t.me/'):
        return '@' + channel_link.replace('http://t.me/', '')
    elif channel_link.startswith('@'):
        return channel_link
    elif '/' not in channel_link and not channel_link.startswith('-100'):
        return '@' + channel_link
    
    # Для числовых ID оставляем как есть
    return channel_link

# ===== ОТЛАДОЧНЫЕ ФУНКЦИИ =====

async def debug_get_user_bots(telegram_id: int):
    """Отладочная функция для проверки ботов пользователя"""
    async with aiosqlite.connect('subscription_bot.db') as db: 
        cursor = await db.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        user_record = await cursor.fetchone()
        
        if not user_record:
            logging.debug(f"Пользователь {telegram_id} не найден")
            return []
        
        user_db_id = user_record[0]
        
        cursor = await db.execute("SELECT * FROM bots WHERE user_id = ?", (user_db_id,))
        bots = await cursor.fetchall()
        logging.debug(f"Все боты для пользователя {telegram_id} (db_id: {user_db_id}): {bots}")
        return bots

async def debug_check_database(telegram_id: int):
    """Отладочная функция для проверки состояния базы данных"""
    async with aiosqlite.connect('subscription_bot.db') as db:
        logging.debug(f"=== DEBUG DATABASE FOR USER {telegram_id} ===")
        
        cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = await cursor.fetchone()
        logging.debug(f"User record: {user}")
        
        if user:
            user_db_id = user[0]
            
            cursor = await db.execute("SELECT * FROM bots")
            all_bots = await cursor.fetchall()
            logging.debug(f"All bots in database: {all_bots}")
            
            cursor = await db.execute("SELECT * FROM bots WHERE user_id = ?", (user_db_id,))
            user_bots = await cursor.fetchall()
            logging.debug(f"User bots (user_db_id={user_db_id}): {user_bots}")
        else:
            logging.debug("User not found in database")
        
        logging.debug("=== END DEBUG ===")
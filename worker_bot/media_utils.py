"""
worker_bot/media_utils.py
Утилиты для работы с медиа-файлами
"""

import logging
from aiogram.types import Message, CallbackQuery
from aiogram.types import InputMediaPhoto, InputMediaVideo, InputMediaDocument
from aiogram.exceptions import TelegramBadRequest
from .keyboards import main_menu_kb

async def send_media_with_message(
    message: Message, 
    file_id: str, 
    file_type: str, 
    text: str, 
    button_url: str = None, 
    keyboard = None,
    parse_mode: str = "HTML"
):
    """
    Отправляет медиа-файл с сообщением
    
    Args:
        message: Объект сообщения
        file_id: ID файла в Telegram
        file_type: Тип файла (photo, video, document)
        text: Текст сообщения
        button_url: Ссылка для кнопки
        keyboard: Клавиатура (если None, используется main_menu_kb)
        parse_mode: Режим парсинга (HTML, Markdown, None)
    """
    # Проверяем, есть ли валидный файл
    if not file_id or not file_type:
        logging.warning("⚠️ Попытка отправить медиа без file_id или file_type")
        reply_markup = keyboard or main_menu_kb(button_url)
        await message.answer(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
        return
    
    try:
        reply_markup = keyboard or main_menu_kb(button_url)
        
        if file_type == 'photo':
            await message.answer_photo(
                photo=file_id,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        elif file_type == 'video':
            await message.answer_video(
                video=file_id,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        elif file_type == 'document':
            await message.answer_document(
                document=file_id,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            logging.warning(f"⚠️ Неизвестный тип файла: {file_type}")
            await message.answer(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
    except Exception as e:
        logging.error(f"❌ Ошибка отправки медиа: {e}")
        # Если не удалось отправить медиа, отправляем просто текст
        await message.answer(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )

async def edit_media_message(
    callback: CallbackQuery, 
    file_id: str, 
    file_type: str, 
    text: str, 
    button_url: str = None, 
    keyboard = None,
    parse_mode: str = "HTML"
):
    """
    Редактирует сообщение с медиа
    
    Args:
        callback: Callback запрос
        file_id: ID файла в Telegram
        file_type: Тип файла (photo, video, document)
        text: Текст сообщения
        button_url: Ссылка для кнопки
        keyboard: Клавиатура (если None, используется main_menu_kb)
        parse_mode: Режим парсинга (HTML, Markdown, None)
    """
    # Проверяем, есть ли валидный файл
    if not file_id or not file_type:
        logging.warning("⚠️ Попытка редактировать медиа без file_id или file_type")
        reply_markup = keyboard or main_menu_kb(button_url)
        try:
            await callback.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer("✅ Сообщение не изменилось", show_alert=False)
            else:
                raise e
        return
    
    try:
        reply_markup = keyboard or main_menu_kb(button_url)
        
        if file_type == 'photo':
            await callback.message.edit_media(
                media=InputMediaPhoto(media=file_id, caption=text, parse_mode=parse_mode),
                reply_markup=reply_markup
            )
        elif file_type == 'video':
            await callback.message.edit_media(
                media=InputMediaVideo(media=file_id, caption=text, parse_mode=parse_mode),
                reply_markup=reply_markup
            )
        elif file_type == 'document':
            await callback.message.edit_media(
                media=InputMediaDocument(media=file_id, caption=text, parse_mode=parse_mode),
                reply_markup=reply_markup
            )
        else:
            logging.warning(f"⚠️ Неизвестный тип файла: {file_type}")
            await callback.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("✅ Сообщение не изменилось", show_alert=False)
        else:
            # Если не удалось редактировать медиа, пробуем редактировать текст
            try:
                await callback.message.edit_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            except TelegramBadRequest as e2:
                if "message is not modified" in str(e2):
                    await callback.answer("✅ Сообщение не изменилось", show_alert=False)
                else:
                    raise e2
    except Exception as e:
        logging.error(f"❌ Ошибка редактирования медиа: {e}")
        # Если не удалось редактировать медиа, редактируем текст
        try:
            await callback.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await callback.answer("✅ Сообщение не изменилось", show_alert=False)
            else:
                raise e

#coding=utf-8
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.constants import ParseMode
from dotenv import load_dotenv

import os
import re
import sys
import logging
import telegram
import sqlite3
from datetime import datetime, timezone

import storage

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')

logger = logging.getLogger(__name__)

_db_conn = None


def _get_db_connection():
    """Lazily open (and initialize) the sqlite3 connection used for analytics."""
    global _db_conn
    if _db_conn is None:
        _db_conn = storage.get_connection()
        storage.init_db(_db_conn)
    return _db_conn


def _record_activity(update):
    """AC-3: record activity for the current user, independent of the handler."""
    try:
        conn = _get_db_connection()
        user_id = update.effective_user.id
        now = datetime.now(timezone.utc)
        storage.record_activity(conn, user_id, now)
    except sqlite3.Error:
        logger.exception('Не удалось записать активность пользователя')

def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([BOT_TOKEN])


async def send_message(update, context, text, buttons=None):
    """Отправляет сообщение в Telegram чат. 
    Принимает на вход три параметра: update, context, текстом и кнопки.
    """
    logger.info('Отправляю сообщение')
    try:
        chat_id = update.effective_chat.id

        reply_markup = None
        if buttons:
            keyboard = [InlineKeyboardButton(text, url=url) for text, url in buttons.items()]
            reply_markup = InlineKeyboardMarkup([keyboard])

        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
    except telegram.error.TelegramError as error:
        logging.exception(error)
    else:
        logging.debug(f'Бот отправил сообщение: "{text}"')


async def start(update, context):
    """Send a message when the command /start is issued."""
    logger.info("/start")
    _record_activity(update)

    await update.message.reply_html(
        "Привет, я бот для готовки ссылок для переписки в Ватсап и Телеграм. "
        "Чтобы получить ссылку просто пришли номер телефона."
    )

async def help_command(update, context):
    logger.info("/help")
    _record_activity(update)
    await update.message.reply_text(
        "Просто отправь мне номер телефона в любом  "
        "виде, и я пришлю две кнопки.\n\n"
        "Всё дело в том, чтобы начать переписку с "
        "новым контактом, его надо сохранить в "
        "телефонную книгу. Зачем всё это! Начни общение сразу."
    )


async def send_links(update: Update, context) -> None:
    """Send a WhatsApp link for a given phone number."""
    PHONE_REGEX = r'^(\s*)?(\+)?([- _():=+]?\d[- _():=+]?){10,14}(\s*)?$'

    _record_activity(update)

    msg = update.message.text.strip()
    match = re.sub(r'\D', '', msg)

    if re.match(PHONE_REGEX, match):
        if match.startswith("8"):
            match = "7" + match[1:]
        elif "7" not in match and "8" not in match:
            match = "7" + match

        buttons = {
            "Телеграм 🥏": f"t.me/{match}",
            "Ватсап 🪀": f"https://wa.me/{match}"
        }
        await send_message(update, context, "Выбери синюю кнопку или зелёную::", buttons=buttons)
    else:
        msg = "В этом сообщении телефонных номеров не обнаружил. Попробуйте ещё раз."
        await send_message(update, context, msg)


async def stats_command(update, context) -> None:
    """AC-4/AC-5: reply with usage stats to the admin only; silent for everyone else."""
    logger.info("/stats")
    user_id = update.effective_user.id

    if not storage.is_admin(user_id, os.getenv("ADMIN_ID")):
        return

    conn = _get_db_connection()
    now = datetime.now(timezone.utc)
    stats = storage.get_stats(conn, now)

    await update.message.reply_text(
        f"Уникальных пользователей: {stats['total']}\n"
        f"Активных за 7 дней: {stats['active']}"
    )


def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(
            f'Не установлены переменные окружения: '
            f'{BOT_TOKEN}'
        )
        sys.exit('Непорядок с переменными окружения')

    builder = Application.builder().token(BOT_TOKEN)

    proxy_url = os.getenv('TELEGRAM_PROXY_URL')
    if proxy_url:
        builder = builder.proxy_url(proxy_url).get_updates_proxy_url(proxy_url)

    application = builder.build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))

    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        send_links
    ))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    log_format = (
        '%(asctime)s, %(levelname)s,'
        ' %(message)s, %(funcName)s, %(lineno)d'
    )

    logging.basicConfig(
        format=log_format,
        level=logging.INFO
    )

    main()

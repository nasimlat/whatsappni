#coding=utf-8
from telegram.ext import Application, CommandHandler, MessageHandler, InlineQueryHandler, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import InlineQueryResultArticle, InputTextMessageContent
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
        username = update.effective_user.username or update.effective_user.first_name
        now = datetime.now(timezone.utc)
        storage.record_activity(conn, user_id, now, username=username)
    except sqlite3.Error:
        logger.exception('Не удалось записать активность пользователя')

def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([BOT_TOKEN])


def _buttons_to_markup(buttons):
    """Convert a {label: url} dict into a single-row InlineKeyboardMarkup."""
    keyboard = [InlineKeyboardButton(text, url=url) for text, url in buttons.items()]
    return InlineKeyboardMarkup([keyboard])


async def send_message(update, context, text, buttons=None):
    """Отправляет сообщение в Telegram чат.
    Принимает на вход три параметра: update, context, текстом и кнопки.
    """
    logger.info('Отправляю сообщение')
    try:
        chat_id = update.effective_chat.id

        reply_markup = _buttons_to_markup(buttons) if buttons else None

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
        "Привет! Пришли номер телефона — и я дам ссылки, чтобы сразу написать "
        "человеку в Telegram или WhatsApp — даже не сохраняя контакт."
    )

async def help_command(update, context):
    logger.info("/help")
    _record_activity(update)
    await update.message.reply_text(
        "Пришли мне номер телефона в любом формате — и я дам кнопки, чтобы "
        "открыть чат в Telegram или WhatsApp, плюс сами ссылки: тапни по "
        "ссылке, чтобы её скопировать.\n\n"
        "Ещё меня можно звать прямо в любом чате: начни писать моё имя (@…) "
        "и номер — и отправь ссылки собеседнику, не заходя сюда.\n\n"
        "Обычно, чтобы написать новому человеку, его номер сначала надо "
        "сохранить в контакты. Со мной это не нужно — жми и пиши."
    )


PHONE_REGEX = r'^(\s*)?(\+)?([- _():=+]?\d[- _():=+]?){10,14}(\s*)?$'


def normalize_phone(text: str):
    """Take a raw string, strip non-digits, normalize a leading '8' to '7'
    (or prepend '7' if neither '7' nor '8' is present), and return the
    digits-only phone number, or None if the input is not a valid phone
    number.
    """
    digits = re.sub(r'\D', '', text)

    if not re.match(PHONE_REGEX, digits):
        return None

    if digits.startswith("8"):
        digits = "7" + digits[1:]
    elif "7" not in digits and "8" not in digits:
        digits = "7" + digits

    return digits


def _build_link_buttons(match):
    return {
        "Telegram 🥏": f"https://t.me/+{match}",
        "WhatsApp 🪀": f"https://wa.me/{match}"
    }


def _build_copyable_links_text(buttons):
    """Render a {label: url} dict as labeled, tap-to-copy <code> blocks.

    Each link is its own block separated by a blank line so they're easy to
    tap individually without hitting the wrong one, and the "https://" prefix
    is dropped to keep the copyable text short — Telegram auto-links
    t.me/wa.me addresses anyway.
    """
    blocks = []
    for label, url in buttons.items():
        short = url.removeprefix("https://")
        blocks.append(f"{label} — <code>{short}</code>")
    return "\n\n".join(blocks)


async def send_links(update: Update, context) -> None:
    """Send a WhatsApp link for a given phone number."""
    _record_activity(update)

    match = normalize_phone(update.message.text)

    if match is not None:
        buttons = _build_link_buttons(match)
        text = (
            "Готово! Жми кнопку — откроется чат 👇\n\n"
            "Или тапни ссылку, чтобы скопировать:\n\n"
            + _build_copyable_links_text(buttons)
        )
        await send_message(update, context, text, buttons=buttons)
    else:
        msg = "Не нашёл здесь номера. Пришли его ещё раз — можно в любом формате."
        await send_message(update, context, msg)


async def inline_query(update, context) -> None:
    """Inline mode: given a raw query, answer with links to Telegram/WhatsApp
    chats for the phone number found in it, or empty results if none."""
    query = update.inline_query.query
    normalized = normalize_phone(query)

    if normalized is None:
        await update.inline_query.answer([])
        return

    buttons = _build_link_buttons(normalized)
    reply_markup = _buttons_to_markup(buttons)
    message_text = _build_copyable_links_text(buttons)

    result = InlineQueryResultArticle(
        id="links",
        title="Ссылки для этого номера",
        input_message_content=InputTextMessageContent(
            message_text, parse_mode=ParseMode.HTML
        ),
        reply_markup=reply_markup,
    )

    await update.inline_query.answer([result])


def _format_timestamp(iso_str):
    """Приводит ISO-строку из БД к читаемому 'YYYY-MM-DD HH:MM'."""
    return datetime.fromisoformat(iso_str).strftime("%Y-%m-%d %H:%M")


async def stats_command(update, context) -> None:
    """AC-4/AC-5: reply with usage stats to the admin only; silent for everyone else. Сам админ в статистику не входит."""
    logger.info("/stats")
    user_id = update.effective_user.id

    if not storage.is_admin(user_id, os.getenv("ADMIN_ID")):
        return

    conn = _get_db_connection()
    now = datetime.now(timezone.utc)
    stats = storage.get_stats(conn, now, exclude_user_id=user_id)
    users = storage.get_user_list(conn, exclude_user_id=user_id)

    lines = [
        f"Уникальных пользователей: {stats['total']}",
        f"Активных за 7 дней: {stats['active']}",
    ]

    if users:
        lines.append("")
        for u in users:
            label = f"@{u['username']}" if u["username"] else f"id{u['user_id']}"
            lines.append(
                f"{label} — впервые: {_format_timestamp(u['first_seen'])}, "
                f"последний раз: {_format_timestamp(u['last_seen'])}, "
                f"сообщений: {u['messages_count']}"
            )

    await update.message.reply_text("\n".join(lines))


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
    application.add_handler(InlineQueryHandler(inline_query))

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

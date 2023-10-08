#coding=utf-8
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler
from telegram.ext import filters
from telegram import Update, ParseMode
from dotenv import load_dotenv

import os
import re
import sys
import logging
import telegram

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

updater = Updater(token=BOT_TOKEN, use_context=True)

logger = logging.getLogger(__name__)

def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([BOT_TOKEN])


def send_message(update, context, text):
    """Отправляет сообщение в Telegram чат. 
    Принимает на вход три параметра: update, context и строку с текстом.
    """
    logger.info('Отправляю сообщение')
    try:
        chat_id = update.effective_chat.id
        context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML
        )
    except telegram.error.TelegramError as error:
        logging.exception(error)
    else:
        logging.debug(f'Бот отправил сообщение: "{text}"')


def start(update, context):
    """Send a message when the command /start is issued."""
    logger.info("/start")
    # send_message(
    #     context.bot,
    #     update.message.chat_id,
    #     "Привет, я бот для готовки ссылок для переписки в WhatsApp. "
    #     "Чтобы получить ссылку просто пришли номер телефона."
    # )
    update.message.reply_html(
        "Привет, я бот для готовки ссылок для переписки в WhatsApp. "
        "Чтобы получить ссылку просто пришли номер телефона."
    )

def help_command(update, context):
    logger.info("/help")
    update.message.reply_text(
        "Просто отправь мне номер телефона в любом  "
        "виде, и я пришлю WhatsApp-ссылку для диалога.\n\n"
        "Всё дело в том, чтобы начать переписку с "
        "новым контактом, контакт оный необходимо сохранить в "
        "телефонную книгу. Бот же избавляет от лишних "
        "пальцедвижений, и позволяет начать диалог "
        "минуя захламление телефонной книги."
    )


def send_whatsapp_link(update: Update, context: CallbackContext) -> None:
    """Send a WhatsApp link for a given phone number."""
    PHONE_REGEX = r'^(\s*)?(\+)?([- _():=+]?\d[- _():=+]?){10,14}(\s*)?$'

    msg = update.message.text.strip()
    match = re.sub(r'\D', '', msg)

    if re.match(PHONE_REGEX, match):
        if match.startswith("8"):
            match = "7" + match[1:]
        elif "7" not in match and "8" not in match:
            match = "7" + match

        whatsapp_number = f"https://wa.me/{match}"

        send_message(update, context, whatsapp_number)
        # context.bot.send_message(chat_id=update.effective_chat.id, text=whatsapp_number, parse_mode=ParseMode.HTML)
    else:
        msg = "В этом сообщении телефонных номеров не обнаружил. "
        "Попробуйте ещё раз."
        send_message(update, context, msg)
        # context.bot.send_message(chat_id=update.effective_chat.id, text="В этом сообщении телефонных номеров я не обнаружил!")
    # database = UserDatabase()
    # database.write_to_db(msg)

# Add the command and message handlers to the updater
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('help', help_command))
updater.dispatcher.add_handler(MessageHandler(filters.text_messages & ~filters.command_messages, send_whatsapp_link))

def main() -> None:
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(
            f'Не установлены переменные окружения: '
            f'{BOT_TOKEN}'
        )
        sys.exit('Непорядок с переменными окружения')

    updater.start_polling()
    updater.idle()

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

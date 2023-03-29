from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler
from telegram.ext.filters import Filters
from telegram import Update, ParseMode
from dotenv import load_dotenv
# from stats import log_usage

import os
import re
import logging
import telegram

load_dotenv()


BOT_TOKEN = os.getenv('BOT_TOKEN')

updater = Updater(token=os.environ.get('BOT_TOKEN', None), use_context=True)

logger = logging.getLogger(__name__)


def send_message(update, context, message):
    """Отправляет сообщение в Telegram чат. 
    Принимает на вход три параметра: update, context и строку с текстом.
    """
    logger.info('Отправляю сообщение')
    try:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode=ParseMode.HTML
        )
    except telegram.error.TelegramError as error:
        logging.error(error)
    else:
        logging.debug(f'Бот отправил сообщение: "{message}"')


def start(update, context):
    """Send a message when the command /start is issued."""
    logger.info("/start")
    update.message.reply_html(
        f"Привет, я бот для готовки ссылки на переписку в WhatsApp. " 
        "Напиши номер телефона и я пришлю ссылку на переписку в WhatsApp."
    )

def help_command(update, context):
    logger.info("/help")
    update.message.reply_html(
        f"Просто отправьте мне номер телефона в любом формате, и я пришлю "
        "WhatsApp-ссылку для диалога."
    )


def send_whatsapp_link(update: Update, context: CallbackContext) -> None:
    """Send a WhatsApp link for a given phone number."""
    PHONE_REGEX = r'^(\s*)?(\+)?([- _():=+]?\d[- _():=+]?){10,14}(\s*)?$'

    message = update.message.text.strip()
    match = re.sub(r'\D', '', message)

    if re.match(PHONE_REGEX, match):
        if match.startswith("8"):
            match = "7" + match[1:]
        elif "7" not in match and "8" not in match:
            match = "7" + match

        whatsapp_number = f"https://wa.me/{match}"

        send_message(update, context, whatsapp_number)
        # context.bot.send_message(chat_id=update.effective_chat.id, text=whatsapp_number, parse_mode=ParseMode.HTML)
    else:
        message = "В этом сообщении телефонных номеров не обнаружил. "
        "Попробуйте ещё раз."
        send_message(update, context, message)
        # context.bot.send_message(chat_id=update.effective_chat.id, text="В этом сообщении телефонных номеров я не обнаружил!")


# Add the command and message handlers to the updater
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('help', help_command))
updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, send_whatsapp_link))

def main() -> None:
    """Start the bot."""
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

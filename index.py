from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler
from telegram.ext.filters import Filters
from telegram import Update, ParseMode
# from stats import log_usage

import os
import re

from dotenv import load_dotenv

load_dotenv()  # loads the configs from .env

updater = Updater(token=os.environ.get('BOT_TOKEN', None), use_context=True)


def start(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Привет, я бот для отправки ссылки на переписку в WhatsApp. \
            Напишите номер телефона и я пришлю ссылку на переписку в \
            WhatsApp"
    )


def help_command(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Просто отправьте мне номер телефона в любом формате, \
            и я пришлю ссылку на переписку в WhatsApp."
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
        context.bot.send_message(chat_id=update.effective_chat.id, text=whatsapp_number, parse_mode=ParseMode.HTML)
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="В этом сообщении телефонных номеров я не обнаружил!")


# Add the command and message handlers to the updater
updater.dispatcher.add_handler(CommandHandler('start', start))
updater.dispatcher.add_handler(CommandHandler('help', help_command))
updater.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, send_whatsapp_link))

def main() -> None:
    """Start the bot."""
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()

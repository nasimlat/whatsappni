import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram.constants import ParseMode
from bot import send_message
from bot import send_links


@pytest.mark.asyncio
async def test_send_message():
    update = MagicMock()
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    await send_message(update, context, 'Test message')

    context.bot.send_message.assert_called_with(
        chat_id=update.effective_chat.id,
        text='Test message',
        parse_mode=ParseMode.HTML
    )


@pytest.mark.asyncio
async def test_send_whatsapp_link_valid_number():
    # Создаем мок-объекты для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    update.message.text = "+79345678901"

    await send_whatsapp_link(update, context)

    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    assert kwargs['text'] == "https://wa.me/79345678901"


@pytest.mark.asyncio
async def test_send_link_valid_number_1():
    # Создаем мок-объекты для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    update.message.text = "89345678901"

    await send_whatsapp_link(update, context)

    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    assert kwargs['text'] == "https://wa.me/79345678901"


@pytest.mark.asyncio
async def test_send_link_valid_number_2():
    # Создаем мок-объекты для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    update.message.text = "8(934)567-89-01"

    await send_whatsapp_link(update, context)

    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    assert kwargs['text'] == "https://wa.me/79345678901"


@pytest.mark.asyncio
async def test_send_link_valid_number_3():
    # Создаем мок-объекты для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    update.message.text = "Вот его номер: 89345678901"

    await send_whatsapp_link(update, context)

    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    assert kwargs['text'] == "https://wa.me/79345678901"


@pytest.mark.asyncio
async def test_send_whatsapp_link_invalid_number():
    # Создаем мок-объекты для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    update.message.text = "invalid number"

    await send_whatsapp_link(update, context)

    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    assert kwargs['text'] == "В этом сообщении телефонных номеров не обнаружил. Попробуйте ещё раз."

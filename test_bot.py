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
        reply_markup=None,
        parse_mode=ParseMode.HTML
    )


@pytest.mark.asyncio
async def test_send_whatsapp_link_valid_number():
    # Создаем мок-объекты для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    update.message.text = "+79345678901"

    await send_links(update, context)

    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    buttons = kwargs['reply_markup'].inline_keyboard[0]
    whatsapp_button = next(b for b in buttons if 'wa.me' in b.url)
    assert whatsapp_button.url == "https://wa.me/79345678901"


@pytest.mark.asyncio
async def test_send_link_valid_number_1():
    # Создаем мок-объекты для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    update.message.text = "89345678901"

    await send_links(update, context)

    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    buttons = kwargs['reply_markup'].inline_keyboard[0]
    whatsapp_button = next(b for b in buttons if 'wa.me' in b.url)
    assert whatsapp_button.url == "https://wa.me/79345678901"


@pytest.mark.asyncio
async def test_send_link_valid_number_2():
    # Создаем мок-объекты для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    update.message.text = "8(934)567-89-01"

    await send_links(update, context)

    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    buttons = kwargs['reply_markup'].inline_keyboard[0]
    whatsapp_button = next(b for b in buttons if 'wa.me' in b.url)
    assert whatsapp_button.url == "https://wa.me/79345678901"


@pytest.mark.asyncio
async def test_send_link_valid_number_3():
    # Создаем мок-объекты для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    update.message.text = "Вот его номер: 89345678901"

    await send_links(update, context)

    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    buttons = kwargs['reply_markup'].inline_keyboard[0]
    whatsapp_button = next(b for b in buttons if 'wa.me' in b.url)
    assert whatsapp_button.url == "https://wa.me/79345678901"


@pytest.mark.asyncio
async def test_send_whatsapp_link_invalid_number():
    # Создаем мок-объекты для update и context
    update = MagicMock()
    context = MagicMock()
    context.bot.send_message = AsyncMock()

    update.message.text = "invalid number"

    await send_links(update, context)

    context.bot.send_message.assert_called_once()
    args, kwargs = context.bot.send_message.call_args
    assert kwargs['text'] == "В этом сообщении телефонных номеров не обнаружил. Попробуйте ещё раз."


# --- Analytics: user activity tracking (AC-3) and /stats admin command (AC-4, AC-5) ---
#
# storage.py is a new, still-stub pure module (see storage.py / test_storage.py for its
# own unit tests). These tests exercise the *integration* between bot.py's handlers and
# storage.py, which bot.py does not call/define yet — they are expected to FAIL until
# bot.py is wired up in the GREEN phase.
#
# Assumed contract encoded by these tests (for the GREEN implementer):
#   - bot.py accesses storage via `import storage; storage.record_activity(...)` (module
#     attribute access, not `from storage import record_activity`), so monkeypatching
#     `storage.record_activity`/`storage.is_admin`/`storage.get_stats` here takes effect.
#   - the new `stats_command` handler replies via `update.message.reply_text(...)`,
#     matching the existing `help_command` pattern in bot.py.
#   - `from bot import stats_command` is done locally inside each test (not at module
#     level) because bot.py does not define it yet; a module-level import would break
#     collection for this whole file. This is deliberate per the RED-phase brief, which
#     explicitly forbids stubbing bot.py in this phase.

import storage


def make_update(text=None, user_id=4242):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.text = text
    update.message.reply_html = AsyncMock()
    update.message.reply_text = AsyncMock()
    return update


def make_context():
    context = MagicMock()
    context.bot.send_message = AsyncMock()
    return context


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "handler_name, message_text",
    [
        pytest.param("start", None, id="AC-3-start"),
        pytest.param("help_command", None, id="AC-3-help_command"),
        pytest.param("send_links", "+79345678901", id="AC-3-send_links"),
    ],
)
async def test_ac3_handlers_record_user_activity(monkeypatch, handler_name, message_text):
    """AC-3: активность фиксируется независимо от хендлера (/start, /help, send_links)."""
    import bot

    handler = getattr(bot, handler_name)
    expected_user_id = 13579
    update = make_update(text=message_text, user_id=expected_user_id)
    context = make_context()

    mock_record = MagicMock()
    monkeypatch.setattr(storage, "record_activity", mock_record)

    await handler(update, context)

    mock_record.assert_called_once()
    called_values = list(mock_record.call_args.args) + list(mock_record.call_args.kwargs.values())
    assert expected_user_id in called_values


@pytest.mark.asyncio
async def test_ac4_stats_command_admin_receives_formatted_counts(monkeypatch):
    """AC-4: /stats от ADMIN_ID отвечает "Уникальных пользователей: {total}\\nАктивных за 7 дней: {active}"."""
    monkeypatch.setattr(storage, "is_admin", MagicMock(return_value=True))
    monkeypatch.setattr(storage, "get_stats", MagicMock(return_value={"total": 5, "active": 2}))

    from bot import stats_command

    update = make_update(user_id=777)
    context = make_context()

    await stats_command(update, context)

    update.message.reply_text.assert_called_once_with(
        "Уникальных пользователей: 5\nАктивных за 7 дней: 2"
    )


@pytest.mark.asyncio
async def test_ac5_stats_command_non_admin_gets_no_response(monkeypatch):
    """AC-5: /stats от user_id != ADMIN_ID не отправляет ответа (тихий игнор, без утечки данных)."""
    monkeypatch.setattr(storage, "is_admin", MagicMock(return_value=False))
    monkeypatch.setattr(storage, "get_stats", MagicMock(return_value={"total": 5, "active": 2}))

    from bot import stats_command

    update = make_update(user_id=999)
    context = make_context()

    await stats_command(update, context)

    update.message.reply_text.assert_not_called()
    context.bot.send_message.assert_not_called()

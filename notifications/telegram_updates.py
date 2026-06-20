"""Telegram bot update dispatcher.

A single ``handle_update`` entry point processes one Telegram ``Update`` dict.
Both the production webhook view and the development long-polling command feed
updates through here, so bot behaviour lives in exactly one place.
"""

import logging

from django.conf import settings

from .telegram_bot import _send_bot_message_sync

logger = logging.getLogger(__name__)


def handle_update(update: dict) -> None:
    """Process a single Telegram Update (from the webhook or the poller)."""
    if not isinstance(update, dict):
        return

    message = update.get("message") or update.get("edited_message")
    if not message:
        # Other update types (callback_query, etc.) aren't handled yet.
        return

    chat_id = (message.get("chat") or {}).get("id")
    if not chat_id:
        return

    text = (message.get("text") or "").strip()

    # Commands look like "/start" or "/start <payload>" (optionally
    # "/start@BotName" in groups).
    command = text.split(maxsplit=1)[0].split("@")[0] if text else ""

    if command == "/start":
        _handle_start(chat_id, message)
    else:
        _handle_fallback(chat_id)


def _open_app_markup():
    """Inline keyboard that opens the Mini App, when a usable HTTPS URL exists.

    Telegram only accepts ``web_app`` buttons over HTTPS, so in local dev (where
    ``FRONTEND_URL`` is typically ``http://localhost``) we return ``None`` and
    callers fall back to plain text.
    """
    app_url = getattr(settings, "FRONTEND_URL", "")
    if app_url.startswith("https://"):
        return {
            "inline_keyboard": [
                [{"text": "Open Bita Business", "web_app": {"url": app_url}}]
            ]
        }
    return None


def _handle_start(chat_id, message):
    first_name = (message.get("from") or {}).get("first_name", "").strip()
    greeting = f"Hi {first_name}!" if first_name else "Hi!"
    markup = _open_app_markup()

    text = (
        f"{greeting} Welcome to <b>Bita Business</b>.\n\n"
        "Manage your inventory, orders and finances right inside Telegram."
    )
    if markup:
        text += "\n\nTap the button below to open the app."
    else:
        app_url = getattr(settings, "FRONTEND_URL", "")
        if app_url:
            text += f"\n\nOpen the app: {app_url}"

    _send_bot_message_sync(chat_id, text, reply_markup=markup)


def _handle_fallback(chat_id):
    markup = _open_app_markup()
    text = (
        "I can't chat much yet 🙂 — open <b>Bita Business</b> to manage your "
        "business."
    )
    if not markup:
        app_url = getattr(settings, "FRONTEND_URL", "")
        if app_url:
            text += f"\n\nOpen the app: {app_url}"
    _send_bot_message_sync(chat_id, text, reply_markup=markup)

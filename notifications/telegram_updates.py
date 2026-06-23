"""Telegram bot update dispatcher.

A single ``handle_update`` entry point processes one Telegram ``Update`` dict.
Both the production webhook view and the development long-polling command feed
updates through here, so bot behaviour lives in exactly one place.
"""

import logging

from django.conf import settings

from .telegram_bot import (
    _answer_callback_query_sync,
    _edit_message_text_sync,
    _send_bot_message_sync,
)

logger = logging.getLogger(__name__)


def handle_update(update: dict) -> None:
    """Process a single Telegram Update (from the webhook or the poller)."""
    if not isinstance(update, dict):
        return

    callback_query = update.get("callback_query")
    if callback_query:
        _handle_callback_query(callback_query)
        return

    message = update.get("message") or update.get("edited_message")
    if not message:
        # Any other update type we asked for but don't act on yet.
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
    from_user = message.get("from") or {}
    first_name = (from_user.get("first_name") or "").strip()
    username = from_user.get("username")
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

    # Keep a linked account's stored handle current, then surface any business
    # invitations that were waiting for this person to start the bot.
    try:
        from business.telegram_invites import (
            deliver_pending_invitations,
            remember_telegram_username,
        )

        remember_telegram_username(chat_id, username)
        deliver_pending_invitations(chat_id, username)
    except Exception:
        logger.exception("Error delivering pending invitations on /start")


def _handle_callback_query(callback_query):
    """Process a tapped inline button (currently invitation Accept/Reject)."""
    callback_id = callback_query.get("id")
    data = callback_query.get("data") or ""
    from_user = callback_query.get("from") or {}
    telegram_id = from_user.get("id")
    username = from_user.get("username")

    message = callback_query.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    message_id = message.get("message_id")

    parts = data.split(":")
    if len(parts) != 3 or parts[0] != "inv":
        _answer_callback_query_sync(callback_id)
        return

    _, action, invitation_id = parts
    try:
        from business.telegram_invites import process_invitation_callback

        result = process_invitation_callback(
            action, invitation_id, telegram_id, username
        )
    except Exception:
        logger.exception("Error processing invitation callback %s", data)
        _answer_callback_query_sync(
            callback_id, text="Something went wrong. Please try again."
        )
        return

    _answer_callback_query_sync(
        callback_id,
        text=result.get("answer"),
        show_alert=result.get("alert", False),
    )
    new_text = result.get("text")
    if new_text and chat_id and message_id:
        # Omitting reply_markup drops the keyboard once the choice is final.
        markup = None if result.get("clear") else result.get("reply_markup")
        _edit_message_text_sync(chat_id, message_id, new_text, reply_markup=markup)


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

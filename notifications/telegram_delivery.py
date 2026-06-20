"""Render Notifications for delivery as Telegram bot messages.

Turns a :class:`~notifications.models.Notification` into the HTML text and
inline keyboard used by :func:`notifications.tasks.send_telegram_notification_task`.
"""

import html
import logging

from django.conf import settings

from .deep_links import deep_link_for_notification

logger = logging.getLogger(__name__)

_TYPE_EMOJI = {
    "info": "ℹ️",
    "warning": "⚠️",
    "error": "⛔",
    "success": "✅",
}


def format_notification(notification):
    """Return ``(html_text, reply_markup)`` for a Telegram DM.

    ``reply_markup`` is an "Open in app" Mini App button when ``FRONTEND_URL`` is
    an HTTPS origin (Telegram rejects ``web_app`` buttons otherwise), else None.
    """
    emoji = _TYPE_EMOJI.get(notification.notification_type, "🔔")
    title = html.escape(notification.title or "")
    message = html.escape(notification.message or "")

    text = f"{emoji} <b>{title}</b>"
    if message:
        text += f"\n\n{message}"

    return text, _app_markup(notification)


def _app_markup(notification):
    base = getattr(settings, "FRONTEND_URL", "")
    if not base.startswith("https://"):
        return None

    data = notification.data or {}
    deep_link = data.get("deep_link") or deep_link_for_notification(
        notification.event_type, data
    )
    # Deep links share the Mini App's route structure (e.g. bita://app/orders/123
    # → /orders/123). Anything unexpected falls back to the notifications list.
    if isinstance(deep_link, str) and deep_link.startswith("bita://app"):
        path = deep_link[len("bita://app") :] or "/notifications"
    else:
        path = "/notifications"

    url = base.rstrip("/") + path
    return {"inline_keyboard": [[{"text": "Open in app", "web_app": {"url": url}}]]}

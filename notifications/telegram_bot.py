"""Outbound Telegram Bot API messaging.

Used to DM users directly from the bot — e.g. delivering the login credentials
of an account that was just created through the Mini App contact/email flow.

Higher-level callers should use :func:`send_bot_message`, which dispatches via
Celery when enabled and otherwise sends synchronously. Failures are logged and
swallowed so a bot hiccup never breaks the calling request.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org"
_TIMEOUT = 10


def _send_bot_message_sync(telegram_id, text):
    """Send a single message via the Telegram Bot API. Returns True on success."""
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.warning("send_bot_message: TELEGRAM_BOT_TOKEN not configured")
        return False
    if not telegram_id:
        logger.warning("send_bot_message: no telegram_id")
        return False

    try:
        resp = requests.post(
            f"{_API_BASE}/bot{bot_token}/sendMessage",
            json={
                "chat_id": int(telegram_id),
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning(
                "send_bot_message: Telegram API returned %s: %s",
                resp.status_code,
                resp.text[:500],
            )
            return False
        return True
    except Exception:
        logger.exception("send_bot_message: failed to message telegram_id=%s", telegram_id)
        return False


def send_bot_message(telegram_id, text):
    """Send a Telegram DM to ``telegram_id``, async via Celery when enabled.

    Mirrors :func:`notifications.service.send_email_notification`: when
    ``settings.EMAIL_USE_CELERY`` is set the work is queued; otherwise it is sent
    synchronously. Enqueue failures fall back to a synchronous send.
    """
    if getattr(settings, "EMAIL_USE_CELERY", False):
        from .tasks import send_bot_message_task

        try:
            send_bot_message_task.delay(telegram_id, text)
            return
        except Exception:
            logger.exception(
                "Could not enqueue bot message for %s; sending synchronously",
                telegram_id,
            )

    _send_bot_message_sync(telegram_id, text)

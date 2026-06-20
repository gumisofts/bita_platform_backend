"""Telegram Bot API client.

Two responsibilities:

* **Outbound messaging** — :func:`send_bot_message` DMs users (e.g. delivering
  the login credentials of an account created through the Mini App flow). It
  dispatches via Celery when enabled and otherwise sends synchronously; failures
  are logged and swallowed so a bot hiccup never breaks the calling request.
* **Bot administration / updates** — :func:`set_webhook`, :func:`delete_webhook`,
  :func:`get_webhook_info` and :func:`get_updates` back the management commands
  that register the production webhook or run the dev long-polling loop.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org"
_TIMEOUT = 10

# The update types we care about — keeps Telegram from sending us everything.
ALLOWED_UPDATES = ["message", "edited_message", "callback_query"]


def _bot_token():
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.warning("Telegram bot token (TELEGRAM_BOT_TOKEN) is not configured")
    return token


def _api_call(method, payload=None, *, timeout=_TIMEOUT):
    """Call a Bot API ``method`` and return its ``result``, or ``None`` on error.

    Never raises — network/HTTP/JSON problems are logged and reported as ``None``
    so callers (request handlers, Celery tasks, polling loop) stay resilient.
    """
    token = _bot_token()
    if not token:
        return None
    try:
        resp = requests.post(
            f"{_API_BASE}/bot{token}/{method}",
            json=payload or {},
            timeout=timeout,
        )
        data = resp.json()
    except Exception:
        logger.exception("Telegram %s call errored", method)
        return None

    if resp.status_code != 200 or not data.get("ok"):
        logger.warning(
            "Telegram %s failed (HTTP %s): %s",
            method,
            resp.status_code,
            str(data)[:500],
        )
        return None
    return data.get("result")


# ─── Outbound messaging ─────────────────────────────────────────────────────


def _send_bot_message_sync(telegram_id, text, reply_markup=None):
    """Send a single message via the Telegram Bot API. Returns True on success."""
    if not telegram_id:
        logger.warning("send_bot_message: no telegram_id")
        return False

    payload = {
        "chat_id": int(telegram_id),
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup

    return _api_call("sendMessage", payload) is not None


def send_bot_message(telegram_id, text, reply_markup=None):
    """Send a Telegram DM to ``telegram_id``, async via Celery when enabled.

    Mirrors :func:`notifications.service.send_email_notification`: when
    ``settings.EMAIL_USE_CELERY`` is set the work is queued; otherwise it is sent
    synchronously. Enqueue failures fall back to a synchronous send.
    """
    if getattr(settings, "EMAIL_USE_CELERY", False):
        from .tasks import send_bot_message_task

        try:
            send_bot_message_task.delay(telegram_id, text, reply_markup)
            return
        except Exception:
            logger.exception(
                "Could not enqueue bot message for %s; sending synchronously",
                telegram_id,
            )

    _send_bot_message_sync(telegram_id, text, reply_markup=reply_markup)


# ─── Webhook administration & polling ───────────────────────────────────────


def set_webhook(url, secret_token=None):
    """Register ``url`` as the bot's webhook. Returns the API result or None."""
    payload = {"url": url, "allowed_updates": ALLOWED_UPDATES}
    if secret_token:
        payload["secret_token"] = secret_token
    return _api_call("setWebhook", payload)


def delete_webhook(drop_pending_updates=False):
    """Remove the bot's webhook (required before long-polling can be used)."""
    return _api_call("deleteWebhook", {"drop_pending_updates": drop_pending_updates})


def get_webhook_info():
    """Return Telegram's current webhook configuration for the bot."""
    return _api_call("getWebhookInfo")


def get_updates(offset=None, timeout=30):
    """Long-poll for updates. Returns a (possibly empty) list of Update dicts.

    ``offset`` should be the last seen ``update_id + 1`` to acknowledge prior
    updates. The HTTP timeout is set above the long-poll ``timeout`` so the
    connection isn't cut while Telegram holds it open waiting for activity.
    """
    payload = {"timeout": timeout, "allowed_updates": ALLOWED_UPDATES}
    if offset is not None:
        payload["offset"] = offset
    return _api_call("getUpdates", payload, timeout=timeout + _TIMEOUT) or []

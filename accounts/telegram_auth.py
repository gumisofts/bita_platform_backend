import hashlib
import hmac
import json
import time
import urllib.parse

from django.conf import settings


def _verify_webapp_signature(raw: str) -> dict:
    """
    Verify a Telegram WebApp data-check signature (HMAC-SHA256) and return the
    parsed key/value payload (``hash`` removed).

    This is the scheme Telegram uses for both Mini App ``initData`` and the
    payload returned by ``requestContact`` — sorted ``key=value`` pairs joined by
    ``\\n``, signed with ``HMAC_SHA256("WebAppData", bot_token)`` as the secret.

    Raises ValueError on missing token, missing/invalid hash, or expired
    auth_date (> 24 h).
    """
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is not configured. Add it to your .env file."
        )

    parsed = dict(urllib.parse.parse_qsl(raw, strict_parsing=False))
    received_hash = parsed.pop("hash", None)

    if not received_hash:
        raise ValueError("Missing hash in Telegram payload")

    # Build the data-check-string: sorted key=value pairs joined by \n
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))

    # HMAC-SHA256("WebAppData", bot_token) → secret key
    secret_key = hmac.new(
        b"WebAppData",
        bot_token.encode(),
        hashlib.sha256,
    ).digest()

    # HMAC-SHA256(secret_key, data_check_string) → expected hash
    expected_hash = hmac.new(
        secret_key,
        check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise ValueError("Invalid Telegram signature")

    auth_date = int(parsed.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        raise ValueError("Telegram payload has expired")

    return parsed


def verify_init_data(init_data_raw: str) -> dict:
    """
    Verify the Telegram Mini App initData HMAC-SHA256 signature and
    return the parsed payload including the nested ``user`` dict.

    Raises ValueError on missing token, invalid signature, or expired auth_date (> 24 h).
    """
    parsed = _verify_webapp_signature(init_data_raw)

    # Parse the nested user JSON string if present
    user_raw = parsed.get("user")
    if user_raw:
        try:
            parsed["user"] = json.loads(user_raw)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("Invalid user JSON in initData")

    return parsed


def verify_contact_data(contact_raw: str) -> dict:
    """
    Verify the signed payload returned by the Mini App ``requestContact`` flow and
    return the nested ``contact`` dict (``user_id``, ``phone_number``,
    ``first_name``, optionally ``last_name``).

    The ``raw`` string is a query-string of the form
    ``contact=<json>&auth_date=<ts>&hash=<sig>`` signed with the same WebAppData
    scheme as ``initData``.

    Raises ValueError on missing token, invalid signature, expired auth_date,
    or missing/invalid contact JSON.
    """
    parsed = _verify_webapp_signature(contact_raw)

    contact_raw_json = parsed.get("contact")
    if not contact_raw_json:
        raise ValueError("Missing contact in Telegram payload")

    try:
        contact = json.loads(contact_raw_json)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Invalid contact JSON in Telegram payload")

    if not isinstance(contact, dict) or not contact.get("phone_number"):
        raise ValueError("Telegram contact is missing a phone number")

    return contact

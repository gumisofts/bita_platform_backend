import hashlib
import hmac
import json
import time
import urllib.parse

from django.conf import settings


def verify_init_data(init_data_raw: str) -> dict:
    """
    Verify the Telegram Mini App initData HMAC-SHA256 signature and
    return the parsed payload including the nested ``user`` dict.

    Raises ValueError on missing token, invalid signature, or expired auth_date (> 24 h).
    """
    bot_token = getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is not configured. " "Add it to your .env file."
        )

    parsed = dict(urllib.parse.parse_qsl(init_data_raw, strict_parsing=False))
    received_hash = parsed.pop("hash", None)

    if not received_hash:
        raise ValueError("Missing hash in initData")

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
        raise ValueError("Invalid initData signature")

    auth_date = int(parsed.get("auth_date", 0))
    if time.time() - auth_date > 86400:
        raise ValueError("initData has expired")

    # Parse the nested user JSON string if present
    user_raw = parsed.get("user")
    if user_raw:
        try:
            parsed["user"] = json.loads(user_raw)
        except (json.JSONDecodeError, TypeError):
            raise ValueError("Invalid user JSON in initData")

    return parsed

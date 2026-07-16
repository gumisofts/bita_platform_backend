import logging

import requests
from django.conf import settings

from ..base import BaseSmsBackend

logger = logging.getLogger(__name__)


def to_msisdn(phone_number: str) -> str:
    """Convert a locally-stored phone number (e.g. ``"911639555"``) to the
    251-prefixed MSISDN the SMS Ethiopia API expects
    (e.g. ``"251911639555"``).
    """
    digits = "".join(ch for ch in str(phone_number or "") if ch.isdigit())
    if digits.startswith("251"):
        return digits
    if digits.startswith("0"):
        digits = digits[1:]
    return f"251{digits}"


class SmsEthiopiaBackend(BaseSmsBackend):
    """Sends SMS via the SMS Ethiopia HTTP API.

    Configuration (see .env.example):
      SMS_ETHIOPIA_API_KEY  — required, sent as the "KEY" header.
      SMS_ETHIOPIA_BASE_URL — defaults to https://smsethiopia.et/api/sms/send

    Reference request::

        curl -X POST https://smsethiopia.et/api/sms/send \\
          -H "KEY: YOUR_API_KEY" \\
          -H "Content-Type: application/json" \\
          -d '{"msisdn": "251911639555", "text": "Hello World"}'
    """

    TIMEOUT = 10  # seconds

    def send(self, phone_number: str, message: str) -> bool:
        api_key = settings.SMS_ETHIOPIA_API_KEY
        if not api_key:
            logger.error(
                "SmsEthiopiaBackend: SMS_ETHIOPIA_API_KEY is not configured; "
                "dropping SMS to %s",
                phone_number,
            )
            return False

        payload = {"msisdn": to_msisdn(phone_number), "text": message}
        headers = {"KEY": api_key, "Content-Type": "application/json"}

        try:
            response = requests.post(
                settings.SMS_ETHIOPIA_BASE_URL,
                json=payload,
                headers=headers,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
        except requests.RequestException:
            logger.exception(
                "SmsEthiopiaBackend: failed to send SMS to %s", phone_number
            )
            return False

        logger.info("SmsEthiopiaBackend: sent SMS to %s", phone_number)
        return True

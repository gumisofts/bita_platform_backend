import logging

from ..base import BaseSmsBackend

logger = logging.getLogger(__name__)


class ConsoleSmsBackend(BaseSmsBackend):
    """Prints SMS messages to the log/console instead of sending them.

    Used automatically whenever no real provider is configured (see
    ``SMS_BACKEND`` in settings) so local development never requires a live
    SMS account — mirrors Django's console ``EMAIL_BACKEND``.
    """

    def send(self, phone_number: str, message: str) -> bool:
        logger.info("[console-sms] to=%s message=%r", phone_number, message)
        print(f"\n--- SMS to {phone_number} ---\n{message}\n---------------------\n")
        return True

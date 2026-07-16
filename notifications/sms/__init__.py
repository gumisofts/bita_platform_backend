import logging

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


def get_sms_backend():
    """Instantiate the SMS backend configured in ``settings.SMS_BACKEND``.

    Mirrors Django's ``EMAIL_BACKEND`` pattern: the setting holds a dotted
    import path to a ``BaseSmsBackend`` subclass, so swapping providers (or
    using the console backend for local development) is a config change,
    never a code change at the call sites — they only ever call
    :func:`send_sms`.
    """
    backend_cls = import_string(settings.SMS_BACKEND)
    return backend_cls()


def send_sms(phone_number, message) -> bool:
    """Send a single SMS through the currently configured backend.

    Never raises — delivery failures are logged and reported via the
    return value so callers (e.g. OTP flows) can decide how to react.
    """
    if not phone_number:
        logger.warning("send_sms: no phone_number given (message=%r)", message)
        return False

    try:
        return bool(get_sms_backend().send(phone_number, message))
    except Exception:
        logger.exception("send_sms: backend raised while sending to %s", phone_number)
        return False

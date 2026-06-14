import logging

import firebase_admin
from firebase_admin import messaging

logger = logging.getLogger(__name__)

_firebase_initialized = False


def _ensure_firebase_initialized():
    global _firebase_initialized
    if _firebase_initialized:
        return
    try:
        firebase_admin.get_app()
    except ValueError:
        firebase_admin.initialize_app()
    _firebase_initialized = True


def send_notification(fcm_token, title, body, data=None):
    """
    Send a push notification to a single device via FCM.
    All values in `data` must be strings (FCM requirement).
    """
    _ensure_firebase_initialized()
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            token=fcm_token,
            data=data or {},
        )
        messaging.send(message)
        return True
    except messaging.UnregisteredError:
        logger.warning("FCM token is no longer valid: %s…", fcm_token[:20])
        return False
    except Exception as e:
        logger.error("Failed to send FCM notification: %s", e)
        return False


def send_multicast_notification(fcm_tokens, title, body, data=None):
    """
    Send a push notification to multiple devices at once (max 500 per batch).
    Returns the number of successful sends.
    """
    if not fcm_tokens:
        return 0

    _ensure_firebase_initialized()
    success_count = 0
    batch_size = 500

    for i in range(0, len(fcm_tokens), batch_size):
        batch_tokens = fcm_tokens[i : i + batch_size]
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                tokens=batch_tokens,
                data=data or {},
            )
            response = messaging.send_each_for_multicast(message)
            success_count += response.success_count

            for idx, send_response in enumerate(response.responses):
                if send_response.exception:
                    logger.warning(
                        "FCM send failed for token %s…: %s",
                        batch_tokens[idx][:20],
                        send_response.exception,
                    )
        except Exception as e:
            logger.error("Failed to send multicast FCM notification: %s", e)

    return success_count

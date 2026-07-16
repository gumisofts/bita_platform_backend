import logging
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .deep_links import deep_link_for_notification
from .models import Notification, NotificationRecipient

logger = logging.getLogger(__name__)


def send_email_notification(subject, message, recipients, html_message=None):
    """Send an email, asynchronously via Celery when enabled.

    When ``settings.EMAIL_USE_CELERY`` is true the work is queued on the
    ``email-notifications`` queue; otherwise (e.g. local development) it is sent
    synchronously. If enqueuing fails for any reason we fall back to a
    synchronous send so transactional mail is never silently dropped.

    Args:
        subject: Email subject line.
        message: Plain-text body (also used to render the HTML template).
        recipients: A single address or an iterable of addresses.
        html_message: Optional pre-rendered HTML body.
    """
    if isinstance(recipients, str):
        recipients = [recipients]
    recipients = [r for r in (recipients or []) if r]
    if not recipients:
        logger.warning("send_email_notification: no recipients (subject=%r)", subject)
        return

    from .tasks import send_email_task

    if getattr(settings, "EMAIL_USE_CELERY", False):
        try:
            send_email_task.delay(subject, message, recipients, html_message)
            return
        except Exception:
            logger.exception(
                "Could not enqueue email %r; sending synchronously", subject
            )

    from .emails import send_email

    send_email(subject, message, recipients, html_message=html_message)


def send_verification_code_email(email, code, *, purpose="verify your account"):
    """Email a 6-digit verification/one-time code to ``email``.

    Args:
        email: Recipient address.
        code: The raw (un-hashed) verification code to display.
        purpose: Short phrase describing what the code is for, e.g.
            "verify your email" or "reset your password".
    """
    subject = "Your verification code"
    message = (
        f"Your verification code is {code}.\n\n"
        f"Use it to {purpose}. This code expires in 5 minutes.\n\n"
        "If you didn't request this, you can safely ignore this email."
    )
    send_email_notification(subject, message, email)


def send_sms_notification(phone_number, message):
    """Send an SMS, asynchronously via Celery when enabled.

    Mirrors :func:`send_email_notification`: when ``settings.SMS_USE_CELERY``
    is true the work is queued on the ``user-verification`` queue; otherwise
    (e.g. local development) it is sent synchronously through whichever
    backend ``settings.SMS_BACKEND`` points at (console by default). If
    enqueuing fails for any reason we fall back to a synchronous send so
    OTP codes are never silently dropped.

    Args:
        phone_number: Recipient's phone number, in the app's local storage
            form (e.g. "911639555").
        message: Plain-text SMS body.
    """
    if not phone_number:
        logger.warning("send_sms_notification: no phone_number (message=%r)", message)
        return

    from .tasks import send_sms_task

    if getattr(settings, "SMS_USE_CELERY", False):
        try:
            send_sms_task.delay(phone_number, message)
            return
        except Exception:
            logger.exception(
                "Could not enqueue SMS to %s; sending synchronously", phone_number
            )

    from .sms import send_sms

    send_sms(phone_number, message)


def send_verification_code_sms(phone_number, code, *, purpose="verify your account"):
    """SMS a 6-digit verification/one-time code to ``phone_number``.

    Args:
        phone_number: Recipient's phone number, in the app's local storage
            form (e.g. "911639555").
        code: The raw (un-hashed) verification code to display.
        purpose: Short phrase describing what the code is for, e.g.
            "verify your phone" or "reset your password".
    """
    message = (
        f"Your Bita verification code is {code}. Use it to {purpose}. "
        "This code expires in 5 minutes."
    )
    send_sms_notification(phone_number, message)


def _get_business_user_ids(business):
    """Return a list of user ID strings for all employees in a business."""
    from business.models import Employee

    return list(
        Employee.objects.filter(business=business, user__isnull=False)
        .values_list("user_id", flat=True)
        .distinct()
    )


def create_notification(
    *,
    title,
    message,
    event_type,
    business,
    notification_type="info",
    data=None,
    recipient_user_ids=None,
    deduplicate_key=None,
    deduplicate_window_hours=24,
    delivery_methods="platform, push, telegram",
):
    """
    Create a Notification + NotificationRecipient rows and dispatch push via Celery.

    Args:
        title: Notification title.
        message: Notification body text.
        event_type: One of NOTIFICATION_EVENT_CHOICES values.
        business: Business instance this notification belongs to.
        notification_type: info / warning / error / success.
        data: Dict of extra context (item_id, variant_id, etc.).
        recipient_user_ids: Explicit list of user IDs. If None, all business employees.
        deduplicate_key: If set, skip creation when a notification with the same
                         event_type and this key in data was created within the window.
        deduplicate_window_hours: Hours to look back for deduplication.
        delivery_methods: Comma-separated string of delivery methods (e.g., "platform, push, telegram").
    """
    from .tasks import send_push_notification_task, send_telegram_notification_task

    if deduplicate_key:
        cutoff = timezone.now() - timedelta(hours=deduplicate_window_hours)
        if Notification.objects.filter(
            event_type=event_type,
            business=business,
            data__contains={deduplicate_key: data.get(deduplicate_key)},
            created_at__gte=cutoff,
        ).exists():
            logger.debug(
                "Skipping duplicate %s notification for %s",
                event_type,
                data.get(deduplicate_key),
            )
            return None

    payload = dict(data or {})
    if "deep_link" not in payload:
        payload["deep_link"] = deep_link_for_notification(event_type, payload)

    # Wrap ALL db work in a single savepoint so any failure here never
    # poisons the caller's transaction (e.g. order checkout).  A bare
    # `except IntegrityError` without a savepoint leaves PostgreSQL's
    # transaction in an aborted state even though Python swallowed the
    # exception — the outer COMMIT then silently becomes a ROLLBACK.

    delivery_methods = [m.strip() for m in delivery_methods.split(",") if m.strip()]
    try:
        with transaction.atomic():
            notification = Notification.objects.create(
                title=title,
                message=message,
                message_format="text",
                notification_type=notification_type,
                event_type=event_type,
                business=business,
                data=payload,
                delivery_method="push",
            )

            notification.data = {
                **notification.data,
                "notification_id": str(notification.id),
            }
            notification.save(update_fields=["data"])

            if recipient_user_ids is None:
                recipient_user_ids = _get_business_user_ids(business)

            user_id_strings = [str(uid) for uid in recipient_user_ids]

            NotificationRecipient.objects.bulk_create(
                [
                    NotificationRecipient(notification=notification, recipient_id=uid)
                    for uid in recipient_user_ids
                ]
            )

            if "push" in delivery_methods:
                transaction.on_commit(
                    lambda: send_push_notification_task.delay(
                        str(notification.id), user_id_strings
                    )
                )
            if "telegram" in delivery_methods:
                transaction.on_commit(
                    lambda: send_telegram_notification_task.delay(
                        str(notification.id), user_id_strings
                    )
                )

    except Exception:
        logger.warning(
            "create_notification: failed to create '%s' notification for business %s",
            event_type,
            business.pk if business else None,
            exc_info=True,
        )
        return None

    return notification

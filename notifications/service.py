import logging
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .deep_links import deep_link_for_notification
from .models import Notification, NotificationRecipient

logger = logging.getLogger(__name__)


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
    """
    from .tasks import send_push_notification_task

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

    try:
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
    except IntegrityError:
        logger.warning(
            "create_notification: skipping '%s' notification — business %s no longer exists",
            event_type,
            business.pk if business else None,
        )
        return None

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

    transaction.on_commit(
        lambda: send_push_notification_task.delay(str(notification.id), user_id_strings)
    )

    return notification

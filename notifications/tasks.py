import logging

from celery import shared_task

from core.celery.queues import CeleryQueue

logger = logging.getLogger(__name__)


@shared_task(queue=CeleryQueue.Definitions.REAL_TIME_NOTIFICATIONS)
def send_push_notification_task(notification_id, user_ids):
    """
    Fetch the Notification from DB, look up FCM tokens for the given users,
    and deliver via Firebase Cloud Messaging.
    """
    from accounts.models import UserDevice

    from .firebase import send_multicast_notification
    from .models import Notification

    try:
        notification = Notification.objects.get(id=notification_id)
    except Notification.DoesNotExist:
        logger.error("Notification %s not found, skipping push", notification_id)
        return

    tokens = list(
        UserDevice.objects.filter(user_id__in=user_ids)
        .values_list("fcm_token", flat=True)
        .distinct()
    )

    if not tokens:
        logger.info("No FCM tokens found for notification %s", notification_id)
        return

    data = {k: str(v) for k, v in (notification.data or {}).items()}
    data["event_type"] = notification.event_type
    data["notification_id"] = str(notification.id)

    sent = send_multicast_notification(
        fcm_tokens=tokens,
        title=notification.title,
        body=notification.message,
        data=data,
    )
    logger.info(
        "Push notification %s delivered to %d/%d devices",
        notification_id,
        sent,
        len(tokens),
    )


@shared_task(queue=CeleryQueue.Definitions.INVENTORY_ALERTS)
def check_low_stock_task(variant_ids, business_id):
    """
    After an order is completed, check whether any of the sold variants
    have dropped below their item's notify_below threshold.
    Creates a low-stock notification for each one (deduplicated over 24 h).
    """
    from inventories.models import ItemVariant

    from .service import create_notification

    variants = ItemVariant.objects.filter(id__in=variant_ids).select_related(
        "item", "item__business"
    )

    for variant in variants:
        item = variant.item
        if variant.quantity > item.notify_below:
            continue

        create_notification(
            title="Low Stock Alert",
            message=(
                f"{item.name} ({variant.name}) is running low — "
                f"only {variant.quantity} units remaining "
                f"(threshold: {item.notify_below})."
            ),
            event_type="low_stock",
            business=item.business,
            notification_type="warning",
            data={
                "item_id": str(item.id),
                "variant_id": str(variant.id),
                "item_name": item.name,
                "variant_name": variant.name,
                "current_quantity": variant.quantity,
                "threshold": item.notify_below,
            },
            deduplicate_key="variant_id",
            deduplicate_window_hours=24,
        )

from celery import shared_task

from core.celery.queues import CeleryQueue

from .models import Notification


@shared_task
def send_notification():
    # notification = Notification.objects.get(id=notification_id)
    # print("send_notification")
    # return notification
    print("notification task")
    return "send_notification"

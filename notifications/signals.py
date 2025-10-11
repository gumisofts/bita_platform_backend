from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Notification

@receiver(post_save, sender=Notification)
def send_notification_signal(sender, instance, created, **kwargs):
    if created:
        # send_notification.delay(instance.id)
        pass
    
from django.contrib.auth import get_user_model
from django.db import models

from core.models import BaseModel

MESSAGE_FORMAT_CHOICES = [
    ("text", "Text"),
    ("html", "HTML"),
    ("markdown", "Markdown"),
]

MESSAGE_DELIVERY_CHOICES = [
    ("email", "Email"),
    ("push", "Push"),
    ("sms", "SMS"),
    ("all", "All"),
]

NOTIFICATION_TYPE_CHOICES = [
    ("info", "Info"),
    ("warning", "Warning"),
    ("error", "Error"),
    ("success", "Success"),
]

NOTIFICATION_EVENT_CHOICES = [
    ("low_stock", "Low Stock Alert"),
    ("price_change", "Price Change"),
    ("product_updated", "Product Updated"),
    ("restocked", "Restocked"),
    ("order_completed", "Order Completed"),
    ("inventory_movement", "Inventory Movement"),
    ("general", "General"),
]


class Notification(BaseModel):
    title = models.CharField(max_length=255)
    message = models.TextField()
    message_format = models.CharField(
        max_length=255, choices=MESSAGE_FORMAT_CHOICES, default="text"
    )
    notification_type = models.CharField(
        max_length=255, choices=NOTIFICATION_TYPE_CHOICES, default="info"
    )
    event_type = models.CharField(
        max_length=50, choices=NOTIFICATION_EVENT_CHOICES, default="general"
    )
    business = models.ForeignKey(
        "business.Business",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
    )
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivery_method = models.CharField(
        max_length=255, choices=MESSAGE_DELIVERY_CHOICES, default="push"
    )
    send_to_recipients_only = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class NotificationRecipient(models.Model):
    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="recipients"
    )
    recipient = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="recipients"
    )
    is_read = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.recipient.email}: {self.recipient.phone_number} - {self.notification.title}"

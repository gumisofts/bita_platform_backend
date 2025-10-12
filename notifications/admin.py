from django.contrib import admin

from notifications.models import Notification, NotificationRecipient


class NotificationRecipientInline(admin.TabularInline):
    model = NotificationRecipient
    extra = 1


# Register your models here.
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "message", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["title", "message"]
    ordering = ["-created_at"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "title",
                    "message",
                    "message_format",
                    "notification_type",
                    "delivery_method",
                    "send_to_recipients_only",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]
    inlines = [NotificationRecipientInline]


#  title = models.CharField(max_length=255)
#     message = models.TextField()
#     message_format = models.CharField(max_length=255, choices=MESSAGE_FORMAT_CHOICES)
#     notification_type = models.CharField(
#         max_length=255, choices=NOTIFICATION_TYPE_CHOICES
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     delivery_method = models.CharField(max_length=255, choices=MESSAGE_DELIVERY_CHOICES)
#     send_to_recipients_only = models.BooleanField(default=True)

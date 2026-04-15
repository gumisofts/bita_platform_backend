from rest_framework import serializers

from accounts.models import UserDevice

from .models import NOTIFICATION_EVENT_CHOICES, Notification, NotificationRecipient


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        exclude = ["delivery_method", "send_to_recipients_only"]
        read_only_fields = ["event_type", "data", "business"]

    def get_is_read(self, obj):
        return obj.recipients.filter(
            recipient=self.context["request"].user, is_read=True
        ).exists()


class NotificationRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationRecipient
        fields = "__all__"
        depth = 1


class NotificationMarkAsReadSerializer(serializers.Serializer):
    notification_ids = serializers.ListField(child=serializers.UUIDField())


class DeviceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDevice
        fields = ["id", "label", "name", "device_id", "os", "manufacturer"]


class TestPushSerializer(serializers.Serializer):
    device_id = serializers.UUIDField(help_text="ID of the UserDevice to send to.")
    title = serializers.CharField(max_length=255, default="Test Notification")
    body = serializers.CharField(default="This is a test push notification.")
    event_type = serializers.ChoiceField(
        choices=NOTIFICATION_EVENT_CHOICES, default="general", required=False
    )

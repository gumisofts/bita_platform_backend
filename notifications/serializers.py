from rest_framework import serializers

from .models import Notification, NotificationRecipient


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        exclude = ["delivery_method", "send_to_recipients_only"]

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

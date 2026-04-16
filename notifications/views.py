from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import DestroyModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .filters import NotificationFilter
from .models import Notification, NotificationRecipient
from .serializers import (
    DeviceListSerializer,
    NotificationDeleteSerializer,
    NotificationMarkAsReadSerializer,
    NotificationSerializer,
    TestPushSerializer,
)


class NotificationViewSet(ListModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = NotificationFilter

    def get_queryset(self):
        return self.queryset.filter(
            recipients__recipient=self.request.user,
            recipients__is_deleted=False,
        )

    def perform_destroy(self, instance):
        """Soft-delete: mark the recipient record as deleted instead of removing the row."""
        NotificationRecipient.objects.filter(
            notification=instance, recipient=self.request.user
        ).update(is_deleted=True)

    @action(
        detail=False,
        methods=["post"],
        serializer_class=NotificationMarkAsReadSerializer,
        url_path="mark-as-read",
    )
    def mark_as_read(self, request):
        notification_ids = request.data.get("notification_ids", [])
        if not notification_ids:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        NotificationRecipient.objects.filter(
            notification_id__in=notification_ids, recipient=request.user
        ).update(is_read=True)
        return Response({"detail": "Notifications marked as read"})

    @action(
        detail=False,
        methods=["post"],
        serializer_class=NotificationDeleteSerializer,
        url_path="delete",
    )
    def bulk_delete(self, request):
        """Soft-delete multiple notifications at once."""
        serializer = NotificationDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notification_ids = serializer.validated_data["notification_ids"]
        updated = NotificationRecipient.objects.filter(
            notification_id__in=notification_ids,
            recipient=request.user,
            is_deleted=False,
        ).update(is_deleted=True)
        return Response({"detail": f"{updated} notification(s) deleted."})

    @action(detail=False, methods=["get"], serializer_class=DeviceListSerializer)
    def devices(self, request):
        """List all of the current user's registered devices with their active state."""
        from accounts.models import UserDevice

        devices = UserDevice.objects.filter(user=request.user).order_by("-created_at")
        serializer = DeviceListSerializer(devices, many=True)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=["post"],
        serializer_class=TestPushSerializer,
        url_path="test-push",
    )
    def test_push(self, request):
        """Send a test push notification to a specific device."""
        from accounts.models import UserDevice

        from .firebase import send_notification

        serializer = TestPushSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            device = UserDevice.objects.get(
                id=serializer.validated_data["device_id"], user=request.user
            )
        except UserDevice.DoesNotExist:
            return Response(
                {"detail": "Device not found or does not belong to you."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not device.is_active:
            return Response(
                {
                    "detail": "Device is disabled. Enable it first before sending a test push."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        title = serializer.validated_data["title"]
        body = serializer.validated_data["body"]
        event_type = serializer.validated_data.get("event_type", "general")

        success = send_notification(
            fcm_token=device.fcm_token,
            title=title,
            body=body,
            data={
                "event_type": event_type,
                "test": "true",
                "device_name": device.name,
            },
        )

        if success:
            return Response(
                {
                    "detail": f"Test notification sent to {device.name} ({device.label}).",
                    "device": DeviceListSerializer(device).data,
                }
            )
        return Response(
            {
                "detail": "Failed to deliver push notification. Check FCM token validity."
            },
            status=status.HTTP_502_BAD_GATEWAY,
        )

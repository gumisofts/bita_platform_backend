from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .filters import NotificationFilter
from .models import Notification, NotificationRecipient
from .serializers import (
    DeviceListSerializer,
    NotificationMarkAsReadSerializer,
    NotificationSerializer,
    TestPushSerializer,
)


class NotificationViewSet(ListModelMixin, GenericViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filterset_class = NotificationFilter

    def get_queryset(self):
        return self.queryset.filter(recipients__recipient=self.request.user)

    @action(
        detail=False,
        methods=["post"],
        serializer_class=NotificationMarkAsReadSerializer,
    )
    def mark_as_read(self, request):
        notification_ids = request.data.get("notification_ids", [])
        if not notification_ids:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        NotificationRecipient.objects.filter(
            notification_id__in=notification_ids, recipient=request.user
        ).update(is_read=True)

        return Response(
            status=status.HTTP_200_OK, data={"detail": "Notifications marked as read"}
        )

    @action(detail=False, methods=["get"], serializer_class=DeviceListSerializer)
    def devices(self, request):
        """List the current user's registered devices (for picking a test target)."""
        from accounts.models import UserDevice

        devices = UserDevice.objects.filter(user=request.user)
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
            {"detail": "Failed to deliver push notification. Check FCM token validity."},
            status=status.HTTP_502_BAD_GATEWAY,
        )

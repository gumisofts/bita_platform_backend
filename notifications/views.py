from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .models import Notification, NotificationRecipient
from .serializers import NotificationMarkAsReadSerializer, NotificationSerializer


class NotificationViewSet(ListModelMixin, GenericViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

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

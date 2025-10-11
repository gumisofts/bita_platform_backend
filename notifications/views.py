from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer

from rest_framework.decorators import action

from .models import NotificationRecipient


class NotificationViewSet(viewsets.ListModelMixin,viewsets.GenericViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    
    def get_queryset(self):
        return self.queryset.filter(recipients__recipient=self.request.user)
    
    @action(detail=False,methods=['post'])
    def mark_as_read(self,request):
        notification_ids = request.data.get('notification_ids',[])
        NotificationRecipient.objects.filter(notification_id__in=notification_ids,recipient=request.user).update(is_read=True)
        
        return Response(status=status.HTTP_200_OK)
    
    
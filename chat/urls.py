from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import (
    ConversationViewSet,
    MessageViewSet,
    ConversationParticipantViewSet,
    ConversationInvitationViewSet,
)

router = DefaultRouter()

# Register chat endpoints
router.register(r'conversations', ConversationViewSet, basename='conversations')
router.register(r'messages', MessageViewSet, basename='messages')
router.register(r'participants', ConversationParticipantViewSet, basename='participants')
router.register(r'invitations', ConversationInvitationViewSet, basename='invitations')

urlpatterns = router.urls 
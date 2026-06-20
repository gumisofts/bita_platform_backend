from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet, TelegramWebhookView

router = DefaultRouter()
router.register(r"", NotificationViewSet, basename="notification")

urlpatterns = [
    # Telegram pushes bot updates here in production. Listed before the router
    # so the literal path isn't shadowed by the notification detail route.
    path(
        "telegram/webhook/",
        TelegramWebhookView.as_view(),
        name="telegram-webhook",
    ),
] + router.urls

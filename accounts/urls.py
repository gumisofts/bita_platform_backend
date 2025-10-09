from channels.routing import URLRouter
from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.consumers import TestConsumer
from accounts.views import *

auth_router = URLRouter([path("test/", TestConsumer.as_asgi())])

router = DefaultRouter()
router.register(r"users", UserViewSet, basename="users")
router.register(
    r"auth/delete-account", ConfirmDeleteUserDeleteView, basename="delete-user-account"
)
router.register(r"auth", AuthViewset, basename="auth")

router.register(r"user_devices", UserDeviceViewset, basename="user-devices")


urlpatterns = [
    path(
        "token/verify/",
        JWTTokenVerifyView.as_view(),
        name="token-verify",
    ),
] + router.urls

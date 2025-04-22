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
router.register(r"auth/register", RegisterViewset, basename="auth-register")
router.register(
    r"auth/refresh/login", RefreshLoginViewset, basename="auth-refresh-login"
)
router.register(
    r"auth/password/reset", ResetRequestViewset, basename="auth-password-reset"
)
router.register(
    r"auth/password/reset/confirm",
    ConfirmResetPasswordRequestViewset,
    basename="auth-password-reset-confirm",
)
router.register(
    r"auth/password/change", PasswordChangeViewset, basename="auth-password-change"
)
router.register(
    r"auth/password/reset/request",
    ResetPasswordRequestViewset,
    basename="auth-password-reset-request",
)
router.register(r"auth/login", LoginViewset, basename="auth-login")
router.register(
    r"auth/google/login", LoginWithGoogleViewset, basename="auth-google-login"
)
router.register(
    r"auth/verifications/confirm",
    ConfirmVerificationCodeViewset,
    basename="auth-verification-confirm",
)
router.register(
    r"auth/verifications/send",
    SendVerificationCodeViewset,
    basename="auth-verification-send",
)
router.register(r"businesses", BusinessViewSet, basename="businesses")
router.register(r"categories", CategoryViewSet, basename="categories")
router.register(r"roles", RoleViewSet, basename="roles")
router.register(r"addresses", AddressViewSet, basename="addresses")
router.register(r"branches", BranchViewSet, basename="branches")
router.register(r"industries", IndustryViewset, basename="industries")

urlpatterns = [
    path(
        "token/verify/",
        JWTTokenVerifyView.as_view(),
        name="token-verify",
    ),
] + router.urls

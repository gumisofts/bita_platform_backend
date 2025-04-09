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
router.register(r"businesses", BusinessViewSet)
router.register(r"categories", CategoryViewSet)
router.register(r"roles", RoleViewSet)
router.register(r"role-permissions", RolePermissionViewSet)
router.register(r"addresses", AddressViewSet)
router.register(r"branches", BranchViewSet)

urlpatterns = (
    [
        path(
            "token/verify/",
            JWTTokenVerifyView.as_view(),
            name="token_verify",
        ),
        path(
            "password-reset/",
            PasswordResetView.as_view(),
            name="password-reset",
        ),
        path(
            "password-reset-confirm/<uidb64>/<token>/",
            PasswordResetConfirmView.as_view(),
            name="password-reset-confirm",
        ),
        path(
            "phone-change/",
            PhoneChangeRequestView.as_view(),
            name="phone-change",
        ),
        path(
            "phone-change-confirm/<str:uidb64>/<str:token>/",
            PhoneChangeConfirmView.as_view(),
            name="phone-change-confirm",
        ),
        path(
            "email-change/",
            EmailChangeRequestView.as_view(),
            name="email-change",
        ),
        path(
            "email-change-confirm/<str:uidb64>/<str:token>/",
            EmailChangeConfirmView.as_view(),
            name="email-change-confirm",
        ),
        path(
            "employee-invitation/",
            EmployeeInvitationView.as_view(),
            name="employee-invitation",
        ),
        path(
            """
        employee-invitation-confirm/<uuid:business_id>/<uuid:role_id>/<str:uidb64>/<str:token>/
        """,
            EmployeeInvitationConfirmView.as_view(),
            name="employee-invitation-confirm",
        ),
    ]
    + router.urls
)

from channels.routing import URLRouter
from django.urls import path
from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView,
                                   SpectacularSwaggerView)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.consumers import TestConsumer

from .views import (AddressViewSet, BranchViewSet, BusinessViewSet,
                    CategoryViewSet, CustomTokenObtainPairView,
                    EmailChangeConfirmView, EmailChangeRequestView,
                    EmployeeInvitationConfirmView, EmployeeInvitationView,
                    JWTTokenVerifyView, PasswordChangeView,
                    PasswordResetConfirmView, PasswordResetView,
                    PhoneChangeConfirmView, PhoneChangeRequestView,
                    RolePermissionViewSet, RoleViewSet, UserViewSet,
                    api_documentation)

auth_router = URLRouter([path("test/", TestConsumer.as_asgi())])

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"businesses", BusinessViewSet)
router.register(r"categories", CategoryViewSet)
router.register(r"roles", RoleViewSet)
router.register(r"role-permissions", RolePermissionViewSet)
router.register(r"addresses", AddressViewSet)
router.register(r"branches", BranchViewSet)

urlpatterns = (
    [
        path("", api_documentation, name="api_documentation"),
        path(
            "token/",
            CustomTokenObtainPairView.as_view(),
            name="token_obtain_pair",
        ),
        path(
            "token/refresh/",
            TokenRefreshView.as_view(),
            name="token_refresh",
        ),
        path(
            "token/verify/",
            JWTTokenVerifyView.as_view(),
            name="token_verify",
        ),
        path("schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "swagger/",
            SpectacularSwaggerView.as_view(url_name="schema"),
            name="swagger-ui",
        ),
        path(
            "redoc/",
            SpectacularRedocView.as_view(url_name="schema"),
            name="redoc",
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
            "password-change/",
            PasswordChangeView.as_view(),
            name="password-change",
        ),
        path(
            "phone-change/",
            PhoneChangeRequestView.as_view(),
            name="phone-change",
        ),
        path(
            "phone-change-confirm/<uidb64>/<token>/",
            PhoneChangeConfirmView.as_view(),
            name="phone-change-confirm",
        ),
        path(
            "email-change/",
            EmailChangeRequestView.as_view(),
            name="email-change",
        ),
        path(
            "email-change-confirm/<uidb64>/<token>/",
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
        employee-invitation-confirm/<business_id>/<role_id>/<uidb64>/<token>/
        """,
            EmployeeInvitationConfirmView.as_view(),
            name="employee-invitation-confirm",
        ),
    ]
    + router.urls
)

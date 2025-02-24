from channels.routing import URLRouter
from django.urls import include, path
from drf_spectacular.views import (SpectacularAPIView, SpectacularRedocView,
                                   SpectacularSwaggerView)
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.consumers import TestConsumer

from .views import (BusinessViewSet, CustomerViewSet,
                    CustomTokenObtainPairView, EmployeeInvitationAcceptView,
                    EmployeeInvitationCreateView, EmployeeViewSet,
                    JWTTokenVerifyView, PasswordChangeView,
                    PasswordResetConfirmView, PasswordResetView,
                    SupplierViewSet, UserViewSet, api_documentation)

auth_router = URLRouter([path("test/", TestConsumer.as_asgi())])

router = DefaultRouter()
router.register(r"users", UserViewSet)
router.register(r"suppliers", SupplierViewSet, basename="supplier")
router.register(r"customers", CustomerViewSet, basename="customer")
router.register(r"employees", EmployeeViewSet, basename="employee")
router.register(r"businesses", BusinessViewSet)

urlpatterns = [
    path("", api_documentation, name="api_documentation"),
    path("token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", JWTTokenVerifyView.as_view(), name="token_verify"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "swagger/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"
    ),
    path("redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("password-reset/", PasswordResetView.as_view(), name="password-reset"),
    path(
        "password-reset-confirm/<uidb64>/<token>/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("password-change/", PasswordChangeView.as_view(), name="password-change"),
    path(
        "employee/invite/",
        EmployeeInvitationCreateView.as_view(),
        name="employee-invite",
    ),
    path(
        "employee/invite/accept/<uuid:token>/",
        EmployeeInvitationAcceptView.as_view(),
        name="employee-invite-accept",
    ),
] + router.urls

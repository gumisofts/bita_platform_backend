from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from accounts.admin_views import (
    get_user_jwt_token,
    impersonate_user,
    stop_impersonation,
)

urlpatterns = [
    path(
        "docs/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path(
        "",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "admin/impersonate-user/<uuid:user_id>/",
        impersonate_user,
        name="impersonate_user",
    ),
    path(
        "admin/get-user-jwt-token/<uuid:user_id>/",
        get_user_jwt_token,
        name="get_user_jwt_token",
    ),
    path("admin/stop-impersonation/", stop_impersonation, name="stop_impersonation"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("business/", include("business.urls")),
    path("files/", include("files.urls")),
    path("inventories/", include("inventories.urls")),
    path("crms/", include("crms.urls")),
    path("finances/", include("finances.urls")),
    path("markets/", include("markets.urls")),
    path("chat/", include("chat.urls")),
    path("orders/", include("orders.urls")),
    path("notifications/", include("notifications.urls")),
]

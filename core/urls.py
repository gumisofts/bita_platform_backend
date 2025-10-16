from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
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

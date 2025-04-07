from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    # path(
    #     "docs/",
    # ),
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
    path("file/", include("file.urls")),
    path("inventory/", include("inventory.urls")),
    path("crm/", include("crm.urls")),
    path("financial/", include("financials.urls")),
]

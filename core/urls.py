from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),
    # file urls
    path("file/", include("file.urls")),
    # notification-module urls
    path("api/", include("notification.urls")),
    # inventory-module urls
    path("inventory/", include("inventory.urls")),
]

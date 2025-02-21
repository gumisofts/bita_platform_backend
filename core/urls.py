from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("accounts.urls")),

    # notification-module urls
    path('api/', include('notification.urls')),  

]

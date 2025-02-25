from django.urls import include, path
from rest_framework import routers

from .views import FileDownloadView, UploadViewSet

router = routers.DefaultRouter()
router.register(r"upload", UploadViewSet, basename="upload")

# Wire up our API using automatic URL routing.
urlpatterns = [
    path("", include(router.urls)),
    # Add the FileDownloadView URL
    path("download/<str:stored_as>/", FileDownloadView.as_view(), name="file-download"),
]

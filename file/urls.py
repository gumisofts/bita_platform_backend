from django.urls import path, include
from rest_framework import routers
from .views import UploadViewSet, FileDownloadView

router = routers.DefaultRouter()
router.register(r"upload", UploadViewSet, basename="upload")

# Wire up our API using automatic URL routing.
urlpatterns = [
    path("", include(router.urls)),
    # Add the FileDownloadView URL
    path("download/<str:stored_as>/", FileDownloadView.as_view(), name="file-download"),
]

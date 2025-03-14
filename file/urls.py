from django.urls import include, path
from rest_framework import routers

from .views import (
    FileDownloadView,
    GenerateSignedUrlView,
    SaveUploadedFileView,
    UploadViewSet,
)

router = routers.DefaultRouter()
router.register(r"upload", UploadViewSet, basename="file-upload")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "upload/generate-signed-url/",
        GenerateSignedUrlView.as_view(),
        name="generate-signed-url",
    ),
    path(
        "upload/save-uploaded-file/",
        SaveUploadedFileView.as_view(),
        name="save-uploaded-file",
    ),
    path("download/<str:stored_as>/", FileDownloadView.as_view(), name="file-download"),
]

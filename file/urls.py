from django.urls import path, include
from rest_framework import routers
from .views import UploadViewSet, FileDownloadView

router = routers.DefaultRouter()
router.register(r'upload', UploadViewSet, basename="file-upload")

urlpatterns = [
    path('', include(router.urls)),
    path('download/<str:stored_as>/', FileDownloadView.as_view(), name='file-download'),
]
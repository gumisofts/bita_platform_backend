from django.urls import include, path
from rest_framework import routers

from .views import *

router = routers.DefaultRouter()

router.register(r"upload/signed_url", SignUrlViewset, basename="signed-url")
router.register(r"upload/confirm", FileMetaDataViewset, basename="upload-confirm")

urlpatterns = router.urls

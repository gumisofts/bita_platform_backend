from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SuppliedItemViewSetV1, SupplyViewSetV1

router = DefaultRouter()
router.register(r"supplies", SupplyViewSetV1)
router.register(r"supplied-items", SuppliedItemViewSetV1)

urlpatterns = [
    path("", include(router.urls)),
]

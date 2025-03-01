from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SupplyViewSetV1, SuppliedItemViewSetV1

router = DefaultRouter()
router.register(r'supplies', SupplyViewSetV1
                )
router.register(r'supplied-items', SuppliedItemViewSetV1)

urlpatterns = [
    path('', include(router.urls)),
]
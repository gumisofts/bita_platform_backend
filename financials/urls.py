from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OrderItemViewSet, OrderViewSet, TransactionViewSet

router = DefaultRouter()
router.register(r"orders", OrderViewSet)
router.register(r"order-items", OrderItemViewSet)
router.register(r"transactions", TransactionViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

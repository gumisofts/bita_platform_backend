from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BusinessPaymentMethodViewSet,
    OrderItemViewSet,
    OrderViewSet,
    TransactionViewSet,
    get_business_payment_methods,
)

router = DefaultRouter()
router.register(r"orders", OrderViewSet)
router.register(r"order-items", OrderItemViewSet)
router.register(r"transactions", TransactionViewSet)
router.register(
    "business-payment-methods",
    BusinessPaymentMethodViewSet,
    basename="business-payment-method",
)


urlpatterns = [
    path(
        "business/<uuid:business_id>/payment-methods/",
        get_business_payment_methods,
        name="business-payment-methods",
    ),
    path("", include(router.urls)),
]

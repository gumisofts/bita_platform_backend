from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register(r"transactions", TransactionViewset)
router.register(r"payment_methods", PaymentMethodViewset, basename="payment-methods")

router.register(
    r"business_payment_methods",
    BusinessPaymentMethodViewset,
    basename="business-payment-methods",
)


urlpatterns = router.urls

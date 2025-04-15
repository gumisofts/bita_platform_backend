from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register(r"customers", CustomerViewSet, basename="customer")
# router.register(r"giftcards", GiftCardViewSet, basename="giftcard")

urlpatterns = [
    path("", include(router.urls)),
]

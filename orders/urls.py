from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OrderItemViewset, OrderViewset

router = DefaultRouter()
router.register(r"orders", OrderViewset, basename="order")

urlpatterns = [] + router.urls

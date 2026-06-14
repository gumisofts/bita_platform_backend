from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import HomeStatsViewSet, OrderItemViewset, OrderViewset

router = DefaultRouter()
router.register(r"orders", OrderViewset, basename="order")
router.register(r"home", HomeStatsViewSet, basename="home-stats")

urlpatterns = [] + router.urls

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    MarketplaceBusinessViewSet,
    MarketplaceCategoryViewSet,
    MarketplaceProductViewSet,
    MarketplaceStatsViewSet,
)

router = DefaultRouter()

# Main marketplace endpoints
router.register(r"products", MarketplaceProductViewSet, basename="marketplace-products")
router.register(
    r"categories", MarketplaceCategoryViewSet, basename="marketplace-categories"
)
router.register(
    r"businesses", MarketplaceBusinessViewSet, basename="marketplace-businesses"
)
router.register(r"stats", MarketplaceStatsViewSet, basename="marketplace-stats")

urlpatterns = router.urls

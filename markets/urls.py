from rest_framework.routers import DefaultRouter
from django.urls import path, include

from .views import (
    MarketplaceProductViewSet,
    MarketplaceCategoryViewSet,
    MarketplaceBusinessViewSet,
    MarketplaceStatsViewSet
)

router = DefaultRouter()

# Main marketplace endpoints
router.register(r'products', MarketplaceProductViewSet, basename='marketplace-products')
router.register(r'categories', MarketplaceCategoryViewSet, basename='marketplace-categories')
router.register(r'businesses', MarketplaceBusinessViewSet, basename='marketplace-businesses')
router.register(r'stats', MarketplaceStatsViewSet, basename='marketplace-stats')

urlpatterns = router.urls 
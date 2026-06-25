from rest_framework.routers import DefaultRouter

from .views import (
    MarketplaceBusinessViewSet,
    MarketplaceCategoryViewSet,
    MarketplaceProductViewSet,
    MarketplaceReviewViewSet,
    MarketplaceStatsViewSet,
    MarketplaceWaitlistViewSet,
)

router = DefaultRouter()

router.register(r"products", MarketplaceProductViewSet, basename="marketplace-products")
router.register(
    r"categories", MarketplaceCategoryViewSet, basename="marketplace-categories"
)
router.register(
    r"businesses", MarketplaceBusinessViewSet, basename="marketplace-businesses"
)
router.register(r"reviews", MarketplaceReviewViewSet, basename="marketplace-reviews")
router.register(
    r"waitlist", MarketplaceWaitlistViewSet, basename="marketplace-waitlist"
)
router.register(r"stats", MarketplaceStatsViewSet, basename="marketplace-stats")

urlpatterns = router.urls

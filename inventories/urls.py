from rest_framework.routers import DefaultRouter

from inventories.views import *

router = DefaultRouter()
router.register(r"items/variants", ItemVariantViewset, basename="item-variants")
router.register(r"items", ItemViewset, basename="items")
router.register(r"supplies", SupplyViewset, basename="supplies")
router.register(r"groups", GroupViewset, basename="groups")
router.register(r"pricings", PricingViewset, basename="pricings")
router.register(r"supplied_items", SupplyItemViewset, basename="supplied-items")

urlpatterns = [] + router.urls

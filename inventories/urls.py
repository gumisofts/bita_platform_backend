from rest_framework.routers import DefaultRouter

from inventories.views import *

router = DefaultRouter()
router.register(
    r"items/variants/properties", PropertyViewset, basename="item-variants-properties"
)
router.register(r"items/variants/pricings", PricingViewset, basename="pricings")
router.register(r"items/variants", ItemVariantViewset, basename="item-variants")
router.register(r"items", ItemViewset, basename="items")
router.register(r"suppliers", SupplierViewset, basename="suppliers")
router.register(r"supplies", SupplyViewset, basename="supplies")
router.register(r"groups", GroupViewset, basename="groups")
router.register(r"supplied_items", SupplyItemViewset, basename="supplied-items")
router.register(r"movements", InventoryMovementViewSet, basename="inventory-movements")
router.register(
    r"movement-items", InventoryMovementItemViewSet, basename="movement-items"
)

urlpatterns = [] + router.urls

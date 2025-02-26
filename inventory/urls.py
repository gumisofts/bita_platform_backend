from django.urls import path
from django.urls.conf import include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("items", views.ItemViewSet, basename="items")
router.register("categories", views.CategoryViewSet, basename="categories")
router.register("supply", views.SupplyViewSet, basename="supplies")
router.register("store", views.StoreViewSet, basename="stores")
router.register("location", views.LocationViewSet, basename="locations")
router.register("stock-movement", views.StockMovementViewSet)
router.register("reservations", views.SupplyReservationViewSet, basename="reservations")

# items_router = routers.NestedDefaultRouter(router, "items", lookup="item")
# items_router.register("images", views.ItemImageViewSet, basename="item-images")


# URLConf
urlpatterns = router.urls

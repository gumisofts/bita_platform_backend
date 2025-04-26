from rest_framework.routers import DefaultRouter

router = DefaultRouter()

from business.views import *

router.register(r"businesses", BusinessViewset, basename="businesses")
router.register(r"categories", CategoryViewset, basename="categories")
router.register(r"roles", RoleViewset, basename="roles")
router.register(r"addresses", AddressViewset, basename="addresses")
router.register(r"branches", BranchViewset, basename="branches")
router.register(r"industries", IndustryViewset, basename="industries")

urlpatterns = router.urls

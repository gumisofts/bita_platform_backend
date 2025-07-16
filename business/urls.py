from rest_framework.routers import DefaultRouter

router = DefaultRouter()

from business.views import *

router.register(r"businesses", BusinessViewset, basename="businesses")
router.register(r"categories", CategoryViewset, basename="categories")
router.register(r"permissions", BusinessPermissionViewset, basename="permissions")
router.register(r"roles", BusinessRoleViewset, basename="roles")
router.register(r"addresses", AddressViewset, basename="addresses")
router.register(r"branches", BranchViewset, basename="branches")
router.register(r"industries", IndustryViewset, basename="industries")
router.register(r"businessimage", BusinessImageViewset, basename="businessimage")
router.register(
    r"employees/invitations", EmployeeInvitationViewset, basename="employee-invitations"
)
router.register(r"employees", EmployeeViewset, basename="employees")

urlpatterns = router.urls

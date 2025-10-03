from django.db.models import Q
from django.http import Http404
from guardian.backends import ObjectPermissionBackend, check_support
from guardian.shortcuts import ObjectPermissionChecker, assign_perm, get_content_type
from rest_framework import exceptions
from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import User
from business.models import (
    AdditionalBusinessPermissionNames,
    Address,
    Branch,
    Business,
    Employee,
    EmployeeInvitation,
)

# class BusinessPermissionBackend(ObjectPermissionBackend):
#     def has_perm(self, user, perm, obj=None):
#         support, user_obj = check_support(user, obj)
#         if not support:
#             return False

#         if '.' in perm:
#             app_label, _ = perm.split('.', 1)
#             # TODO (David Graham): Check if obj is None or change the method signature
#             if app_label != obj._meta.app_label:  # type: ignore[union-attr]
#                 # Check the content_type app_label when permission
#                 # and obj app labels don't match.
#                 ctype = get_content_type(obj)
#                 if app_label != ctype.app_label:
#                     raise WrongAppError("Passed perm has app label of '%s' while "
#                                         "given obj has app label '%s' and given obj"
#                                         "content_type has app label '%s'" %
#                                         (app_label, obj._meta.app_label, ctype.app_label))   # type: ignore[union-attr]

#         check = ObjectPermissionChecker(user_obj)
#         return check.has_perm(perm, obj)


class BusinessModelObjectPermission(BasePermission):

    def to_generic_action(self, action):
        if action == "list":
            return "view"
        if action == "create":
            return "add"
        if action == "update":
            return "change"
        if action == "destroy":
            return "delete"
        return "change"

    def has_permission(self, request, view):
        return has_business_permission(
            request, view.queryset.model, request.query_params.get("business_id")
        )

    def has_object_permission(self, request, view):

        return has_business_object_permission(
            request,
            view.queryset.model,
            request.query_params.get("business_id"),
            self.to_generic_action(view.action),
        )


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsEmployee(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.employees.filter(user=request.user).exists()


class IsOwnerOrEmployee(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            obj.owner == request.user
            or obj.employees.filter(user=request.user).exists()
        )


def has_business_permission(request, model, business: Business):
    # Assumes that user is authenticated

    user: User = request.user
    employee = Employee.objects.filter(user=user, business=business).first()

    if not employee:
        return False

    return employee.role.permissions.filter(
        content_type__model=model._meta.model_name
    ).exists()


def has_business_object_permission(request, model, business, generic_action="change"):

    user: User = request.user

    employee = Employee.objects.filter(user=user, business=business).first()

    if not employee:
        return False

    if request.method in SAFE_METHODS:
        return employee.role.permissions.filter(
            content_type__model=model._meta.model_name
        ).exists()

    return employee.role.permissions.filter(
        Q(codename=f"{generic_action}_" + model._meta.model_name)
        # | Q(codename="view_" + model._meta.model_name)
        # | Q(codename="delete_" + model._meta.model_name)
        # | Q(codename="change_" + model._meta.model_name)
    ).exists()


class hasBusinessAddressPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        return has_business_object_permission(request, Address, obj.business)


class hasUserPermission(BasePermission):
    def has_permission(self, request, view):
        if view.action == "list" and request.user.is_superuser:
            return True
        elif view.action == "create":
            return True
        if view.action in ["retrieve", "partial_update", "update", "destroy"]:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if view.action in ["partial_update", "update", "destroy", "retrieve"]:
            return obj == request.user or request.user.is_superuser


class hasBusinessPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return True

    def has_object_permission(self, request, view, obj):

        if view.action in ["partial_update", "update", "destroy", "retrieve"]:
            return has_business_object_permission(request, Business, obj)
        return False


class hasBranchPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        return has_business_object_permission(request, Branch, obj.business)


class BusinessAddressPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        # Address can be related to business in two ways:
        # 1. As the main address of a business (obj.business)
        # 2. As an address used by branches (obj.branches.first().business)
        business = None
        if hasattr(obj, "business") and obj.business:
            business = obj.business
        elif obj.branches.exists():
            business = obj.branches.first().business

        if not business:
            return False

        return has_business_object_permission(request, Address, business)


class EmployeeInvitationPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        return has_business_object_permission(request, EmployeeInvitation, obj.business)


class PermissionManager:

    def assign_employee_permissions(self, employee):
        if employee.role.role_name == "Owner":
            self.assign_owner_permissions(employee.business)
        elif employee.role.role_name == "Manager":
            self.assign_manager_permissions(employee.business)
        elif employee.role.role_name == "Employee":
            self.assign_employee_permissions(employee.business)

    ## Roles
    # Owner
    # Business Admin
    # Branch Manager
    # Branch Employee

    def assign_business_admin_permissions(self, user, business):
        perms = [
            perm.value[0] + "_business" for perm in AdditionalBusinessPermissionNames
        ] + ["view_business", "change_business"]
        for perm in perms:
            assign_perm(perm, user, business)

    def assign_owner_permissions(self, user, business):
        perms = [
            perm.value[0] + "_business" for perm in AdditionalBusinessPermissionNames
        ] + ["change_business", "delete_business", "view_business"]
        for perm in perms:
            assign_perm(perm, user, business)

    def assign_manager_permissions(self, user, business, branch):
        branch_manager_perms = [
            AdditionalBusinessPermissionNames.CAN_VIEW_GROUP,
            AdditionalBusinessPermissionNames.CAN_ADD_GROUP,
            AdditionalBusinessPermissionNames.CAN_ADD_CUSTOMER,
            AdditionalBusinessPermissionNames.CAN_VIEW_ITEM,
            AdditionalBusinessPermissionNames.CAN_ADD_ITEM,
            AdditionalBusinessPermissionNames.CAN_VIEW_SUPPLIER,
        ]
        perms = [perm.value[0] + "_branch" for perm in branch_manager_perms]

        for perm in perms:
            assign_perm(perm, user, branch)

        branch_perms = [
            "view_branch",
            "add_branch",
            "change_branch",
        ]
        business_perms = [
            "view_business",
        ]

        for perm in branch_perms:
            assign_perm(perm, user, branch)

        for perm in business_perms:
            assign_perm(perm, user, business)

    def assign_employee_permissions(self, user, business, branch):
        employee_branch_perms = [
            AdditionalBusinessPermissionNames.CAN_VIEW_GROUP,
            AdditionalBusinessPermissionNames.CAN_ADD_GROUP,
            AdditionalBusinessPermissionNames.CAN_ADD_CUSTOMER,
            AdditionalBusinessPermissionNames.CAN_VIEW_ITEM,
            AdditionalBusinessPermissionNames.CAN_ADD_ITEM,
            AdditionalBusinessPermissionNames.CAN_VIEW_SUPPLIER,
            AdditionalBusinessPermissionNames.CAN_ADD_SUPPLIER,
            AdditionalBusinessPermissionNames.CAN_ADD_ITEM_VARIANT,
            AdditionalBusinessPermissionNames.CAN_VIEW_ITEM_VARIANT,
            AdditionalBusinessPermissionNames.CAN_ADD_INVENTORY_MOVEMENT,
            AdditionalBusinessPermissionNames.CAN_VIEW_INVENTORY_MOVEMENT,
        ]
        perms = [perm.value[0] + "_branch" for perm in employee_branch_perms]

        for perm in perms:
            assign_perm(perm, user, branch)

        branch_perms = ["view_branch"]
        business_perms = ["view_business"]

        for perm in branch_perms:
            assign_perm(perm, user, branch)

        for perm in business_perms:
            assign_perm(perm, user, business)


class BusinessLevelPermission(BasePermission):
    """
    The request is authenticated using Django's object-level permissions.
    It requires an object-permissions-enabled backend, such as Django Guardian.

    It ensures that the user is authenticated, and has the appropriate
    `add`/`change`/`delete` permissions on the object using .has_perms.

    This permission can only be applied against view classes that
    provide a `.queryset` attribute.
    """

    perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.can_add_%(model_name)s_business"],
        "PUT": ["%(app_label)s.can_change_%(model_name)s_business"],
        "PATCH": ["%(app_label)s.can_change_%(model_name)s_business"],
        "DELETE": ["%(app_label)s.can_delete_%(model_name)s_business"],
    }

    def get_required_object_permissions(self, method, model_cls):
        kwargs = {
            "app_label": "business",
            "model_name": model_cls._meta.model_name,
        }

        if method not in self.perms_map:
            raise exceptions.MethodNotAllowed(method)

        return [perm % kwargs for perm in self.perms_map[method]]

    def get_binding_object(self, request):
        """
        This method is used to get the binding object for the permission check.
        It can be overridden in subclasses to provide custom logic.
        """
        if request.method != "GET":
            if request.business:
                return request.business

            business = request.data.get("business")
            if not business:
                business = request.data.get("business_id")
            if business:
                request.business = Business.objects.filter(id=business).first()
                return request.business

        return request.business if hasattr(request, "business") else None

    def has_permission(self, request, view):
        user = request.user
        model_cls = view.queryset.model
        if request.method == "POST":
            business = request.data.get("business")
            if not business:
                business = request.data.get("business_id")
            if business:
                request.business = Business.objects.filter(id=business).first()
                perms = self.get_required_object_permissions(request.method, model_cls)
                return user.has_perms(perms, request.business)

        return super().has_permission(request, view)

    def has_object_permission(self, request, view, obj):
        # authentication checks have already executed via has_permission
        queryset = self._queryset(view)
        model_cls = queryset.model
        user = request.user
        business = self.get_binding_object(request)

        perms = self.get_required_object_permissions(request.method, model_cls)

        if not user.has_perms(perms, business):
            # If the user does not have permissions we need to determine if
            # they have read permissions to see 403, or not, and simply see
            # a 404 response.

            if request.method in SAFE_METHODS:
                # Read permissions already checked and failed, no need
                # to make another lookup.
                raise Http404

            read_perms = self.get_required_object_permissions("GET", model_cls)
            if not user.has_perms(read_perms, obj):
                raise Http404

            # Has read permissions.
            return False

        return True

    def _queryset(self, view):
        assert (
            hasattr(view, "get_queryset") or getattr(view, "queryset", None) is not None
        ), (
            "Cannot apply {} on a view that does not set "
            "`.queryset` or have a `.get_queryset()` method."
        ).format(
            self.__class__.__name__
        )

        if hasattr(view, "get_queryset"):
            queryset = view.get_queryset()
            assert queryset is not None, "{}.get_queryset() returned None".format(
                view.__class__.__name__
            )
            return queryset
        return view.queryset


class BranchLevelPermission(BusinessLevelPermission):
    """
    Permission class for branch-level permissions.
    It extends BusinessLevelPermission to ensure that the user has
    the appropriate permissions for branch-related actions.
    """

    perms_map = {
        "GET": [],
        "OPTIONS": [],
        "HEAD": [],
        "POST": ["%(app_label)s.can_add_%(model_name)s_branch"],
        "PUT": ["%(app_label)s.can_change_%(model_name)s_branch"],
        "PATCH": ["%(app_label)s.can_change_%(model_name)s_branch"],
        "DELETE": ["%(app_label)s.can_delete_%(model_name)s_branch"],
    }

    def get_binding_object(self, request):
        """
        This method is used to get the binding object for the permission check.
        It can be overridden in subclasses to provide custom logic.
        """
        return request.branch if hasattr(request, "branch") else None


class GuardianObjectPermissions(BasePermission):
    """
    Custom permission class that properly works with django-guardian for object-level permissions.
    Based on DjangoObjectPermissions but adapted for Guardian.
    """

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": ["%(app_label)s.view_%(model_name)s"],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }

    def get_required_permissions(self, method, model_cls):
        """
        Given a model and an HTTP method, return the list of permission
        codes that the user is required to have.
        """
        kwargs = {
            "app_label": model_cls._meta.app_label,
            "model_name": model_cls._meta.model_name,
        }

        if method not in self.perms_map:
            return []

        return [perm % kwargs for perm in self.perms_map[method]]

    def has_permission(self, request, view):
        """
        Check if user is authenticated.
        """
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Check object-level permissions using django-guardian.
        """
        queryset = self._queryset(view)
        model_cls = queryset.model
        user = request.user
        perms = self.get_required_permissions(request.method, model_cls)

        # Check if user has the required permissions on this specific object
        if not user.has_perms(perms, obj):
            return False

        return True

    def _queryset(self, view):
        """
        Get the queryset from the view.
        """
        if hasattr(view, "get_queryset"):
            queryset = view.get_queryset()
            if queryset is not None:
                return queryset

        if hasattr(view, "queryset") and view.queryset is not None:
            return view.queryset

        raise AssertionError(
            f"Cannot apply {self.__class__.__name__} on a view that "
            f"does not set `.queryset` or have a `.get_queryset()` method."
        )

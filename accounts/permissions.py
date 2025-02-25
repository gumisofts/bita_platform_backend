from rest_framework.permissions import BasePermission
from .models import Business, EmployeeBusiness


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


class hasSupplierPermission(BasePermission):
    def has_permission(self, request, view):
        business = request.query_params.get("business")
        try:
            request_business = EmployeeBusiness.objects.get(
                employee=request.user, business=business
            )
        except EmployeeBusiness.DoesNotExist:
            return False
        if not request_business:
            return False
        if request_business.role < 3 or request.user.is_superuser:
            return True
        return False


class hasCustomerPermission(BasePermission):
    def has_permission(self, request, view):
        business = request.query_params.get("business")
        try:
            business = Business.objects.get(id=business)
        except Business.DoesNotExist:
            return False
        try:
            request_business = EmployeeBusiness.objects.get(
                employee=request.user, business=business
            )
        except EmployeeBusiness.DoesNotExist:
            return False
        if request_business.role < 3 or request.user.is_superuser:
            return True
        return False


class hasEmployeePermission(BasePermission):
    def has_permission(self, request, view):
        business = request.query_params.get("business")
        try:
            request_business = EmployeeBusiness.objects.get(
                employee=request.user, business=business
            )
        except EmployeeBusiness.DoesNotExist:
            return True
        if request_business.role < 3 or request.user.is_superuser:
            return True

    def has_object_permission(self, request, view, obj):
        business = request.query_params.get("business")
        try:
            target_eb = EmployeeBusiness.objects.get(
                employee=obj,
                business=business,
            )
            requester_eb = EmployeeBusiness.objects.get(
                employee=request.user, business=business
            )
        except EmployeeBusiness.DoesNotExist:
            return False
        if request.method == "PATCH":
            if set(request.data.keys()) - {"role"}:
                return False
        if request.user.is_superuser or requester_eb.role < target_eb.role:
            return True
        return False


class hasEmployeeInvitePermission(BasePermission):
    def has_permission(self, request, view):
        business = request.query_params.get("business")
        try:
            request_business = EmployeeBusiness.objects.get(
                employee=request.user, business=business
            )
        except EmployeeBusiness.DoesNotExist:
            return True
        if request_business.role < 3 or request.user.is_superuser:
            return True


class hasBusinessPermission(BasePermission):
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        if view.action in ["list", "create"]:
            return True
        return True

    def has_object_permission(self, request, view, obj):
        if view.action in ["partial_update", "update", "destroy", "retrieve"]:
            return obj.owner == request.user or request.user.is_superuser
        return False

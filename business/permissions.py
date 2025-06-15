from django.db.models import Q
from rest_framework.permissions import SAFE_METHODS, BasePermission

from accounts.models import User
from business.models import Address, Branch, Business, Employee, EmployeeInvitation


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


def has_bussiness_permission(request, model, bussiness: Business):
    if not request.user.is_authenticated:
        return False
    user: User = request.user

    employee = Employee.objects.filter(user=user, bussiness=bussiness).first()

    if not employee:
        return False

    return (
        request.method in SAFE_METHODS
        and employee.role.permissions.filter(
            content_type__model=model._meta.model_name
        ).exists()
    )


def has_bussiness_object_permission(request, model, bussiness):
    if not request.user.is_authenticated:
        return False
    user: User = request.user

    employee = Employee.objects.filter(user=user, business=bussiness).first()

    if not employee:
        return False

    if request.method in SAFE_METHODS:
        return employee.role.permissions.filter(
            content_type__model=model._meta.model_name
        ).exists()

    return employee.role.permissions.filter(
        Q(codename="add_" + model._meta.model_name)
        | Q(codename="view_" + model._meta.model_name)
        | Q(codename="delete_" + model._meta.model_name)
        | Q(codename="change_" + model._meta.model_name)
    ).exists()


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
            return has_bussiness_object_permission(request, Business, obj)
        return False


class hasBranchPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        return has_bussiness_object_permission(request, Branch, obj.business)


class BusinessAddressPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        return has_bussiness_object_permission(request, Address, obj.business)


class EmployeeInvitationPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        return True

    def has_object_permission(self, request, view, obj):
        return has_bussiness_object_permission(
            request, EmployeeInvitation, obj.business
        )

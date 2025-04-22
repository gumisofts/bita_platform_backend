from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import Business, User, Employee

from django.db.models import Q


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

    employee = Employee.objects.filter(user=user, bussiness=bussiness).first()

    if not employee:
        return False
    if request.method in SAFE_METHODS:
        return employee.role.permissions.filter(
            content_type__model=model._meta.model_name
        ).exists()

    return employee.role.permissions.filter(
        codename=Q("add_" + model._meta.model_name)
        | Q("view_" + model._meta.model_name)
        | Q("delete_" + model._meta.model_name)
        | Q("change_" + model._meta.model_name)
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


# class hasSupplierPermission(BasePermission):
#     def has_permission(self, request, view):
#         business = request.query_params.get("business")
#         try:
#             request_business = EmployeeBusiness.objects.get(
#                 employee=request.user, business=business
#             )
#         except EmployeeBusiness.DoesNotExist:
#             return False
#         if not request_business:
#             return False
#         if request_business.role < 3 or request.user.is_superuser:
#             return True
#         return False


# class hasCustomerPermission(BasePermission):
#     def has_permission(self, request, view):
#         business = request.query_params.get("business")
#         try:
#             business = Business.objects.get(id=business)
#         except Business.DoesNotExist:
#             return False
#         try:
#             request_business = EmployeeBusiness.objects.get(
#                 employee=request.user, business=business
#             )
#         except EmployeeBusiness.DoesNotExist:
#             return False
#         if request_business.role < 3 or request.user.is_superuser:
#             return True
#         return False


# class hasEmployeePermission(BasePermission):
#     def has_permission(self, request, view):
#         business = request.query_params.get("business")
#         try:
#             request_business = EmployeeBusiness.objects.get(
#                 employee=request.user, business=business
#             )
#         except EmployeeBusiness.DoesNotExist:
#             return True
#         if request_business.role < 3 or request.user.is_superuser:
#             return True

#     def has_object_permission(self, request, view, obj):
#         business = request.query_params.get("business")
#         try:
#             target_eb = EmployeeBusiness.objects.get(
#                 employee=obj,
#                 business=business,
#             )
#             requester_eb = EmployeeBusiness.objects.get(
#                 employee=request.user, business=business
#             )
#         except EmployeeBusiness.DoesNotExist:
#             return False
#         if request.method == "PATCH":
#             if set(request.data.keys()) - {"role"}:
#                 return False
#         if request.user.is_superuser or requester_eb.role < target_eb.role:
#             return True
#         return False


# class hasEmployeeInvitePermission(BasePermission):
#     def has_permission(self, request, view):
#         business = request.query_params.get("business")
#         try:
#             request_business = EmployeeBusiness.objects.get(
#                 employee=request.user, business=business
#             )
#         except EmployeeBusiness.DoesNotExist:
#             return True
#         if request_business.role < 3 or request.user.is_superuser:
#             return True


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

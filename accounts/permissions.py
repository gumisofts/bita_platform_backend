from rest_framework.permissions import BasePermission
from .models import Business, Employee, EmployeeBusiness


class IsOwnerOrAdmin(BasePermission):
    """
    Only allow owners of an object or admin users to edit or delete it.
    """

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "created_by"):
            return obj.created_by == request.user or request.user.is_staff
        return obj == request.user or request.user.is_staff


class IsBusinessOwnerOrAdmin(BasePermission):
    """
    Allow editing or deleting a Business only if the user is its owner or is an admin.
    """

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user or request.user.is_staff


class EmployeeCreatePermission(BasePermission):
    """
    Allow employee creation only if:
      - The user is the owner of the given business or a staff user, OR
      - The user has an EmployeeBusiness record on that business with role 'Admin'
        (allowed to create Manager or Sales) or role 'Manager' (allowed to create Sales).
    """

    def has_permission(self, request, view):
        if request.method != "POST":
            return True
        business_id = request.data.get("business")
        new_role = request.data.get("role")
        if not business_id or not new_role:
            return False
        try:
            business = Business.objects.get(id=business_id)
        except Business.DoesNotExist:
            return False
        user = request.user
        if business.owner == user or user.is_staff:
            return True
        try:
            requester_eb = EmployeeBusiness.objects.get(
                business=business, employee=user
            )
        except EmployeeBusiness.DoesNotExist:
            return False
        if requester_eb.role == "Admin" and new_role in ("Manager", "Sales"):
            return True
        elif requester_eb.role == "Manager" and new_role == "Sales":
            return True
        return False


class EmployeeUpdatePermission(BasePermission):
    """
    Allow updating an employee’s non-role fields if the user is staff, the creator, or updating their own record.
    And if updating a role using the write-only "business" and "role" fields,
    only allow it if the user is either the owner of that business, staff,
    or has an EmployeeBusiness record on that business with sufficient privileges:
      - 'Admin' can update to Manager or Sales,
      - 'Manager' can update only to Sales.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        base_permission = user.is_staff or obj.id == user.id or obj.created_by == user

        # If no role update is attempted, allow update if base permission holds.
        business = request.data.get("business")
        role = request.data.get("role")
        if not business and not role:
            return base_permission

        # For updates that include a business/role change, check permission for that business.
        try:
            biz = Business.objects.get(id=business)
        except Business.DoesNotExist:
            return False
        if biz.owner == user or user.is_staff:
            return True
        try:
            requester_eb = EmployeeBusiness.objects.get(business=biz, employee=user)
        except EmployeeBusiness.DoesNotExist:
            return False
        if requester_eb.role == "Admin" and role in ("Manager", "Sales"):
            return True
        elif requester_eb.role == "Manager" and role == "Sales":
            return True
        return False


class EmployeeDeletePermission(BasePermission):
    """
    Allow deletion of an EmployeeBusiness instance (and thus removal of an employee's role on a business)
    only if the user is staff or, for at least one business linked to the target, is either
    its owner or has an EmployeeBusiness record with role 'Admin'.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True
        ebs = EmployeeBusiness.objects.filter(employee=obj)
        for eb in ebs:
            if eb.business.owner == user:
                return True
            try:
                requester_eb = EmployeeBusiness.objects.get(
                    business=eb.business, employee=user
                )
            except EmployeeBusiness.DoesNotExist:
                continue
            if requester_eb.role == "Admin":
                return True
        return False


class EmployeeRetrievePermission(BasePermission):
    """
    Allow retrieval if the user is:
      - Retrieving their own record, OR
      - The owner of a business linked to the target employee, OR
      - Has an EmployeeBusiness record on a common business with a higher role.
    """

    def has_object_permission(self, request, view, obj):
        if obj.id == request.user.id:
            return True
        hierarchy = {"Sales": 1, "Manager": 2, "Admin": 3}
        ebs = EmployeeBusiness.objects.filter(employee=obj)
        for eb in ebs:
            if eb.business.owner == request.user:
                return True
            try:
                requester_eb = EmployeeBusiness.objects.get(
                    business=eb.business, employee=request.user
                )
            except EmployeeBusiness.DoesNotExist:
                continue
            if hierarchy.get(requester_eb.role, 0) > hierarchy.get(eb.role, 0):
                return True
        return False


class IsNonEmployeeUser(BasePermission):
    def has_permission(self, request, view):
        if request.method == "POST":
            return not Employee.objects.filter(id=request.user.id).exists()
        return True

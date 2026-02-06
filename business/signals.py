from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import Signal, receiver
from guardian.shortcuts import assign_perm

from accounts.models import User
from business.models import *
from business.permissions import PermissionManager

from . import roles

employee_invitation_status_changed = Signal()


def assign_default_permissions_to_role(role):
    """
    Assign default permissions to a role based on its role_name.
    """
    if not role or not role.role_name:
        return

    permissions_to_assign = []

    if role.role_name == ROLES.OWNER.value:
        # Owner: Full access to all models in _OwnerFullAccessModels
        for model in roles._OwnerFullAccessModels:
            content_type = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(content_type=content_type)
            permissions_to_assign.extend(perms)

    elif role.role_name == ROLES.BUSINESS_ADMIN.value:
        # Business Admin: Full access to _AdminFullAccessModels + read-only to _AdminReadOnlyModels
        for model in roles._AdminFullAccessModels:
            content_type = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(content_type=content_type)
            permissions_to_assign.extend(perms)

        for model in roles._AdminReadOnlyModels:
            content_type = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(
                content_type=content_type, codename__startswith="view_"
            )
            permissions_to_assign.extend(perms)

    elif role.role_name == ROLES.BRANCH_MANAGER.value:
        # Branch Manager: Similar to Business Admin but with branch-specific permissions
        # For now, use Admin permissions as a base
        for model in roles._AdminFullAccessModels:
            content_type = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(content_type=content_type)
            permissions_to_assign.extend(perms)

        for model in roles._AdminReadOnlyModels:
            content_type = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(
                content_type=content_type, codename__startswith="view_"
            )
            permissions_to_assign.extend(perms)

    elif role.role_name == ROLES.EMPLOYEE.value:
        # Employee: Full access to _EmployeeFullAccessModels + read-only to _EmployeeReadOnlyModels
        for model in roles._EmployeeFullAccessModels:
            content_type = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(content_type=content_type)
            permissions_to_assign.extend(perms)

        for model in roles._EmployeeReadOnlyModels:
            content_type = ContentType.objects.get_for_model(model)
            perms = Permission.objects.filter(
                content_type=content_type, codename__startswith="view_"
            )
            permissions_to_assign.extend(perms)

    # Assign permissions to the role
    if permissions_to_assign:
        # Remove duplicates by converting to set and back to list
        unique_permissions = list(set(permissions_to_assign))
        role.permissions.set(unique_permissions)


# @receiver(post_save, sender=User)
# def on_user_created(sender, instance, created, **kwargs):
#     if created:
#         # Create Default Bussiness Branch
#         Business.objects.create(
#             name="Personal Business",
#             owner=instance,
#             business_type="retail",
#         )


@receiver(post_save, sender=Business)
def on_business_created(sender, instance, created, **kwargs):
    if created:
        # Create Default Bussiness Branch
        Branch.objects.create(
            name="Main Branch",
            business=instance,
            address=instance.address,
        )

        # Owner Full Access

        with transaction.atomic():
            # Create Default Bussiness Branch

            owner = Role.objects.create(
                role_name=ROLES.OWNER.value,
                business=instance,
            )
            Role.objects.create(
                role_name=ROLES.EMPLOYEE.value,
                business=instance,
            )
            Role.objects.create(
                role_name=ROLES.BUSINESS_ADMIN.value,
                business=instance,
            )
            Role.objects.create(
                role_name=ROLES.BRANCH_MANAGER.value,
                business=instance,
            )

            # Create Owner Employee
            Employee.objects.create(
                user=instance.owner,
                business=instance,
                role=owner,
                branch=None,
            )
            PermissionManager().assign_owner_permissions(instance.owner, instance)

            # Assign default permissions to all created roles
            for role in Role.objects.filter(business=instance):
                assign_default_permissions_to_role(role)


@receiver(employee_invitation_status_changed)
def on_employee_invitation_status_changed(sender, instance, status, **kwargs):
    # Send Invitation Email Here
    print(instance, status)

    if status == "accepted":
        user = User.objects.filter(
            Q(phone_number=instance.phone_number) | Q(email=instance.email)
        ).first()

        if not user:
            return

        # Check if employee already exists for this user and business
        existing_employee = Employee.objects.filter(
            user=user, business=instance.business
        ).first()

        if not existing_employee:
            # Create Employee if it doesn't exist
            employee = Employee.objects.create(
                user=user,
                business=instance.business,
                role=instance.role,
                branch=instance.branch,
            )
        else:
            # Update existing employee with new role and branch
            employee = existing_employee
            employee.role = instance.role
            employee.branch = instance.branch
            employee.save()

        # Assign permissions based on role
        if instance.role.role_name == ROLES.BUSINESS_ADMIN.value:
            # Assign permissions to the user based on the role
            PermissionManager().assign_business_admin_permissions(
                user, instance.business
            )

        elif instance.role.role_name == ROLES.EMPLOYEE.value:
            # Assign permissions to the user based on the role
            PermissionManager().assign_employee_permissions(
                user, instance.business, instance.branch
            )

        elif instance.role.role_name == ROLES.BRANCH_MANAGER.value:
            # Assign permissions to the user based on the role
            PermissionManager().assign_manager_permissions(
                user, instance.business, instance.branch
            )


@receiver(post_save, sender=Role)
def on_role_created(sender, instance, created, **kwargs):
    """
    Assign default permissions to a role when it's created.
    Only assign if permissions are not already set (to avoid overwriting manual assignments).
    """
    if created and instance.permissions.count() == 0:
        assign_default_permissions_to_role(instance)

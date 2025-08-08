from django.contrib.auth.models import Permission
from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import Signal, receiver
from guardian.shortcuts import assign_perm

from business.models import *
from business.permissions import PermissionManager

from .roles import *

employee_invitation_status_changed = Signal()


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

        Employee.objects.create(
            user=user,
            business=instance.business,
            role=instance.role,
            branch=instance.branch,
        )

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

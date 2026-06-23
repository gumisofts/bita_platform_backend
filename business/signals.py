from django.contrib.auth.models import Permission
from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import Signal, receiver
from guardian.shortcuts import assign_perm

from accounts.models import User
from business.models import *
from business.permissions import PermissionManager

employee_invitation_status_changed = Signal()
employee_invitation_resend = Signal()


def assign_default_permissions_to_role(role):
    """
    Assign default permissions to a role based on its role_name.

    Single source of truth: all four built-in roles are derived from their
    corresponding dict in business.permissions
    (_OWNER_PERMS / _BUSINESS_ADMIN_PERMS / _BRANCH_MANAGER_PERMS / _EMPLOYEE_PERMS).

    _split_perms_by_scope converts each dict into guardian object-level codenames
    (e.g. ``can_view_item_branch`` / ``can_view_customer_business``).
    A small set of standard Django model perms is appended via extra_codenames
    for models outside PERMISSIONED_MODELS (business, role, user).
    """
    from business.permissions import (
        _BRANCH_MANAGER_PERMS,
        _BUSINESS_ADMIN_PERMS,
        _EMPLOYEE_PERMS,
        _OWNER_PERMS,
        _split_perms_by_scope,
    )

    if not role or not role.role_name:
        return

    # Maps each role to (perm_dict, extra_standard_codenames).
    # extra_standard_codenames covers models not in PERMISSIONED_MODELS
    # (business, role, user) that still need a Django model-level perm.
    _ROLE_PERM_MAP: dict[str, tuple[dict, list[str]]] = {
        ROLES.OWNER.value: (
            _OWNER_PERMS,
            ["view_business", "change_business", "view_role", "view_user"],
        ),
        ROLES.BUSINESS_ADMIN.value: (
            _BUSINESS_ADMIN_PERMS,
            ["view_business", "view_role"],
        ),
        ROLES.BRANCH_MANAGER.value: (
            _BRANCH_MANAGER_PERMS,
            [
                "view_business",
                "view_branch",
                "add_branch",
                "change_branch",
                "view_employee",
                "view_role",
            ],
        ),
        ROLES.EMPLOYEE.value: (
            _EMPLOYEE_PERMS,
            ["view_business", "view_branch", "view_employee", "view_role", "view_user"],
        ),
    }

    entry = _ROLE_PERM_MAP.get(role.role_name)
    if not entry:
        return

    perm_dict, extra_codenames = entry
    branch_perms, business_perms = _split_perms_by_scope(perm_dict)

    codenames: set[str] = set()
    codenames.update(branch_perms)
    codenames.update(business_perms)
    codenames.update(extra_codenames)

    if codenames:
        role.permissions.set(list(Permission.objects.filter(codename__in=codenames)))


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
            from inventories.models import Supplier

            Supplier.objects.create(name="Unknown", business=instance)

            owner = Role.objects.create(
                role_name=ROLES.OWNER.value,
                business=instance,
            )
            employee_role = Role.objects.create(
                role_name=ROLES.EMPLOYEE.value,
                business=instance,
            )
            business_admin_role = Role.objects.create(
                role_name=ROLES.BUSINESS_ADMIN.value,
                business=instance,
            )
            branch_manager_role = Role.objects.create(
                role_name=ROLES.BRANCH_MANAGER.value,
                business=instance,
            )

            assign_default_permissions_to_role(owner)
            assign_default_permissions_to_role(employee_role)
            assign_default_permissions_to_role(business_admin_role)
            assign_default_permissions_to_role(branch_manager_role)

            assign_perm("view_business", instance.owner, instance)
            assign_perm("change_business", instance.owner, instance)
            assign_perm("delete_business", instance.owner, instance)

            # Create Owner Employee (guardian permissions applied via post_save signal)
            Employee.objects.create(
                user=instance.owner,
                business=instance,
                role=owner,
                branch=None,
            )


@receiver(employee_invitation_status_changed)
def on_employee_invitation_status_changed(sender, instance, status, **kwargs):

    if status == "accepted":
        user_q = Q()
        if instance.phone_number:
            user_q |= Q(phone_number=instance.phone_number)
        if instance.email:
            user_q |= Q(email=instance.email)
        if instance.telegram_username:
            user_q |= Q(telegram_username=instance.telegram_username)

        if not user_q:
            return

        user = User.objects.filter(user_q).first()

        if not user:
            return

        with transaction.atomic():
            existing_employee = Employee.objects.filter(
                user=user, business=instance.business
            ).first()

            if not existing_employee:
                Employee.objects.create(
                    user=user,
                    business=instance.business,
                    role=instance.role,
                    branch=instance.branch,
                )
            else:
                existing_employee.role = instance.role
                existing_employee.branch = instance.branch
                existing_employee.save()


@receiver(employee_invitation_resend)
def on_employee_invitation_resend(sender, instance, **kwargs):
    # Re-deliver to a linked Telegram account immediately; username-only invites
    # for users who haven't started the bot are picked up on their next /start.
    if instance.telegram_username:
        from business.telegram_invites import notify_user_if_linked

        notify_user_if_linked(instance)
    # TODO: Implement actual email/SMS notification sending


@receiver(post_save, sender=Branch)
def on_branch_created(sender, instance, created, **kwargs):
    """
    When a new branch is created, grant branch-scoped permissions to all
    existing owners and business admins of that business so they have
    immediate access without needing a manual reapply.
    """
    if not created:
        return

    privileged_roles = [ROLES.OWNER.value, ROLES.BUSINESS_ADMIN.value]
    employees = Employee.objects.filter(
        business=instance.business,
        role__role_name__in=privileged_roles,
    ).select_related("user")

    manager = PermissionManager()
    for employee in employees:
        if employee.user:
            manager.assign_branch_scoped_perms_for_branch(employee.user, instance)


@receiver(post_save, sender=Employee)
def on_employee_saved(sender, instance, **kwargs):
    """
    Central hook: assign guardian object-level permissions whenever an employee
    is created or updated (role/branch change included).
    """
    PermissionManager().assign_permissions_for_employee(instance)

from django.contrib.auth.models import Permission
from django.db import transaction
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from accounts.models import *

from .roles import *


@receiver(pre_save, sender=User)
def on_user_created(sender, instance, **kwargs):

    if kwargs.get("send_verification"):
        pass
    # Send verification Token Here


@receiver(post_save, sender=Employee)
def on_employee_created(sender, instance, created, **kwargs):
    if created:
        # Send verification Token Here
        pass
    else:
        # Update verification Token Here
        pass


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
                role_name="Owner",
                business=instance,
            )
            owner_permissions = Permission.objects.filter(
                content_type__model__in=map(
                    lambda item: item._meta.model_name, OwnerFullAccessModels
                )
            )
            owner.permissions.set(owner_permissions)
            Employee.objects.create(
                user=instance.owner,
                business=instance,
                role=owner,
            )

            admin = Role.objects.create(
                role_name="Manager",
                business=instance,
            )

            admin_permissions = Permission.objects.filter(
                Q(codename__startswith="view_")
                & Q(
                    content_type__model__in=map(
                        lambda item: item._meta.model_name, AdminReadOnlyModels
                    )
                )
                | Q(
                    content_type__model__in=map(
                        lambda item: item._meta.model_name, AdminFullAccessModels
                    )
                ),
            )

            admin.permissions.set(admin_permissions)

            employee = Role.objects.create(
                role_name="Employee",
                business=instance,
            )

            employee_permissions = Permission.objects.filter(
                Q(codename__startswith="view_") &
                # | Q(codename__startswith="add_")
                # | Q(codename__startswith="delete_")
                # | Q(codename__startswith="change_"),
                Q(
                    content_type__model__in=map(
                        lambda item: item._meta.model_name, EmployeeReadOnlyModels
                    )
                )
                | Q(
                    content_type__model__in=map(
                        lambda item: item._meta.model_name, EmployeeFullAccessModels
                    )
                ),
            )
            employee.permissions.set(employee_permissions)
    else:
        # Update verification Token Here
        pass

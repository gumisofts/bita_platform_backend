from accounts.models import Role, Employee, Business
from django.contrib.auth.models import Permission
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver([post_save], sender=Business)
def handle_creation_of_default_roles(sender, instance, created, **kwargs):
    pass
    # Create Default Roles for A Business
    # Add Default Permissions for A Business


@receiver([post_save], sender=Employee)
def handle_employee(sender, instance, created, **kwargs):
    pass

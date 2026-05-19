from django.core.management.base import BaseCommand, CommandError

from business.models import Business, Employee, Role
from business.permissions import PermissionManager
from business.signals import assign_default_permissions_to_role


class Command(BaseCommand):
    help = (
        "Reapply default permissions to roles, then to their employees. "
        "Use --business to target a specific business, --role to target specific role IDs, "
        "or run without arguments to reapply permissions to all roles and employees."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--business",
            dest="business_id",
            type=str,
            help="UUID of the business whose roles should be updated.",
        )
        parser.add_argument(
            "--role",
            dest="role_ids",
            nargs="+",
            type=str,
            help="One or more role UUIDs to update.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be updated without making any changes.",
        )

    def handle(self, *args, **options):
        business_id = options["business_id"]
        role_ids = options["role_ids"]
        dry_run = options["dry_run"]

        roles = Role.objects.select_related("business").prefetch_related("employees")

        if role_ids:
            roles = roles.filter(id__in=role_ids)
            if not roles.exists():
                raise CommandError(f"No roles found for the provided IDs: {role_ids}")

        elif business_id:
            try:
                business = Business.objects.get(id=business_id)
            except Business.DoesNotExist:
                raise CommandError(f"Business with ID '{business_id}' does not exist.")
            roles = roles.filter(business=business)

        total = roles.count()
        if total == 0:
            self.stdout.write(self.style.WARNING("No roles found to update."))
            return

        prefix = "[DRY RUN] " if dry_run else ""

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"{prefix}Reapplying permissions to {total} role(s)..."
            )
        )

        roles_list = list(roles)

        for role in roles_list:
            label = f"{role.role_name} (ID: {role.id}, Business: {role.business})"
            if dry_run:
                self.stdout.write(f"  {prefix}Would update role: {label}")
            else:
                assign_default_permissions_to_role(role)
                self.stdout.write(self.style.SUCCESS(f"  Updated role: {label}"))

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"\n{prefix}Reapplying guardian permissions to employees..."
            )
        )

        for role in roles_list:
            self._reapply_user_permissions(role, dry_run, prefix)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{prefix}Done. {total} role(s) and their employees processed."
            )
        )

    def _reapply_user_permissions(self, role, dry_run, prefix):
        employees = Employee.objects.filter(role=role).select_related(
            "user", "business", "branch"
        )
        if not employees.exists():
            self.stdout.write(f"      No employees found for role {role.role_name}.")
            return

        manager = PermissionManager()

        for employee in employees:
            if not employee.user:
                continue

            user_label = f"{employee.user.email} (ID: {employee.user.id})"

            if dry_run:
                self.stdout.write(
                    f"    {prefix}Would reapply guardian permissions for user: {user_label}"
                )
                continue

            manager.assign_permissions_for_employee(employee)

            self.stdout.write(
                self.style.SUCCESS(
                    f"    Reapplied guardian permissions for user: {user_label}"
                )
            )

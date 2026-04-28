"""
Management command: send_test_push

Send a test push notification to one or all devices of a selected user.

Usage examples
--------------
# Interactive — prompts for everything
python manage.py send_test_push

# Non-interactive — send to all active devices of a user
python manage.py send_test_push --user user@example.com \
    --title "Hello" --body "Test message" --all-devices

# Target a specific device by ID
python manage.py send_test_push --user user@example.com \
    --device <device-uuid> --title "Hello" --body "Test message"

# Custom event type (drives deep-link in the app)
python manage.py send_test_push --user user@example.com --all-devices \
    --title "Low Stock" --body "Item X is running low" --event-type low_stock
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from notifications.firebase import send_multicast_notification, send_notification

User = get_user_model()

EVENT_TYPES = [
    "general",
    "low_stock",
    "price_change",
    "product_updated",
    "restocked",
    "order_completed",
    "inventory_movement",
]


class Command(BaseCommand):
    help = "Send a test push notification to a selected user's device(s)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            metavar="EMAIL_OR_PHONE",
            help="Email or phone number of the target user. "
            "Omit to pick interactively.",
        )
        parser.add_argument(
            "--device",
            metavar="DEVICE_ID",
            help="UUID of a specific UserDevice. Omit to pick interactively "
            "(or use --all-devices).",
        )
        parser.add_argument(
            "--all-devices",
            action="store_true",
            default=False,
            help="Send to all active devices of the user instead of a single device.",
        )
        parser.add_argument(
            "--title",
            default="",
            help="Notification title (prompted if omitted).",
        )
        parser.add_argument(
            "--body",
            default="",
            help="Notification body (prompted if omitted).",
        )
        parser.add_argument(
            "--event-type",
            default="general",
            choices=EVENT_TYPES,
            help="Event type — controls the deep-link in the app (default: general).",
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _prompt(self, prompt_text, default=""):
        value = input(f"{prompt_text} [{default}]: ").strip() if default else input(f"{prompt_text}: ").strip()
        return value or default

    def _pick_user(self):
        self.stdout.write("\nSearch user by email or phone number.")
        query = self._prompt("Email / phone")
        users = User.objects.filter(email__icontains=query) | User.objects.filter(
            phone_number__icontains=query
        )
        users = list(users[:20])
        if not users:
            raise CommandError(f"No users found matching '{query}'.")
        if len(users) == 1:
            return users[0]

        self.stdout.write("\nMultiple users found:")
        for idx, u in enumerate(users, start=1):
            self.stdout.write(f"  [{idx}] {u.email or '—'}  |  {u.phone_number or '—'}  |  {u.get_full_name()}")
        choice = self._prompt("Pick number")
        try:
            return users[int(choice) - 1]
        except (ValueError, IndexError):
            raise CommandError("Invalid selection.")

    def _pick_device(self, user):
        from accounts.models import UserDevice

        devices = list(UserDevice.objects.filter(user=user).order_by("-created_at"))
        if not devices:
            raise CommandError(f"User '{user.email}' has no registered devices.")

        self.stdout.write("\nRegistered devices:")
        for idx, d in enumerate(devices, start=1):
            status = self.style.SUCCESS("active") if d.is_active else self.style.ERROR("disabled")
            self.stdout.write(
                f"  [{idx}] {d.name} ({d.label})  |  {d.os}  |  "
                f"token: {d.fcm_token[:24]}…  |  {status}"
            )
        choice = self._prompt("Pick device number")
        try:
            return devices[int(choice) - 1]
        except (ValueError, IndexError):
            raise CommandError("Invalid selection.")

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        from accounts.models import UserDevice
        from notifications.deep_links import deep_link_for_notification

        # ── Resolve user ──────────────────────────────────────────────
        if options["user"]:
            query = options["user"]
            user = (
                User.objects.filter(email=query).first()
                or User.objects.filter(phone_number=query).first()
            )
            if not user:
                raise CommandError(f"No user found with email/phone '{query}'.")
        else:
            user = self._pick_user()

        self.stdout.write(
            f"\nTarget user: {self.style.SUCCESS(user.email or user.phone_number or str(user.pk))}"
            f"  ({user.get_full_name()})"
        )

        # ── Resolve device(s) ─────────────────────────────────────────
        send_to_all = options["all_devices"]
        specific_device_id = options["device"]

        if send_to_all:
            devices = list(UserDevice.objects.filter(user=user, is_active=True))
            if not devices:
                raise CommandError("This user has no active devices.")
        elif specific_device_id:
            try:
                device = UserDevice.objects.get(id=specific_device_id, user=user)
            except UserDevice.DoesNotExist:
                raise CommandError(
                    f"Device '{specific_device_id}' not found for this user."
                )
            if not device.is_active:
                self.stdout.write(
                    self.style.WARNING(f"Device '{device.name}' is disabled — proceeding anyway.")
                )
            devices = [device]
        else:
            devices = [self._pick_device(user)]

        # ── Notification content ──────────────────────────────────────
        title = options["title"] or self._prompt("Title", default="Test Notification")
        body = options["body"] or self._prompt("Body", default="This is a test push notification.")
        event_type = options["event_type"]

        data = {
            "event_type": event_type,
            "test": "true",
            "deep_link": deep_link_for_notification(event_type, {}),
        }

        # ── Send ──────────────────────────────────────────────────────
        self.stdout.write("")

        if send_to_all or len(devices) > 1:
            tokens = [d.fcm_token for d in devices]
            self.stdout.write(
                f"Sending to {len(tokens)} active device(s) via multicast…"
            )
            sent = send_multicast_notification(
                fcm_tokens=tokens,
                title=title,
                body=body,
                data=data,
            )
            if sent == len(tokens):
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Delivered to all {sent} device(s).")
                )
            elif sent > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠ Partially delivered: {sent}/{len(tokens)} device(s) received it."
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR("✗ Delivery failed for all devices. Check FCM tokens / Firebase credentials.")
                )
        else:
            device = devices[0]
            self.stdout.write(
                f"Sending to {device.name} ({device.label})  |  token: {device.fcm_token[:32]}…"
            )
            success = send_notification(
                fcm_token=device.fcm_token,
                title=title,
                body=body,
                data=data,
            )
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Notification delivered to '{device.name}'.")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        "✗ Delivery failed. The FCM token may be stale or Firebase credentials are missing."
                    )
                )

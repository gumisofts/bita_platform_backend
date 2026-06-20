"""
Management command: set_telegram_webhook

Register (or inspect / delete) the Telegram bot webhook used in production.

Usage examples
--------------
# Register the webhook at BACKEND_URL + /notifications/telegram/webhook/
python manage.py set_telegram_webhook

# Register an explicit URL
python manage.py set_telegram_webhook --url https://api.example.com/notifications/telegram/webhook/

# Show the currently registered webhook
python manage.py set_telegram_webhook --info

# Remove the webhook (e.g. before running the dev poller)
python manage.py set_telegram_webhook --delete
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

WEBHOOK_PATH = "/notifications/telegram/webhook/"


class Command(BaseCommand):
    help = "Register, inspect, or delete the Telegram bot webhook."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            help=(
                "Full HTTPS webhook URL. Defaults to BACKEND_URL + "
                f"'{WEBHOOK_PATH}'."
            ),
        )
        parser.add_argument(
            "--delete",
            action="store_true",
            default=False,
            help="Delete the webhook instead of setting it.",
        )
        parser.add_argument(
            "--info",
            action="store_true",
            default=False,
            help="Print the current webhook configuration and exit.",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "TELEGRAM_BOT_TOKEN", ""):
            raise CommandError("TELEGRAM_BOT_TOKEN is not configured.")

        from notifications.telegram_bot import (
            delete_webhook,
            get_webhook_info,
            set_webhook,
        )

        if options["info"]:
            info = get_webhook_info()
            if info is None:
                raise CommandError("Could not fetch webhook info (see logs).")
            self.stdout.write(self.style.SUCCESS("Current webhook:"))
            for key in ("url", "pending_update_count", "last_error_message"):
                if key in info:
                    self.stdout.write(f"  {key}: {info[key]}")
            return

        if options["delete"]:
            if delete_webhook(drop_pending_updates=True) is None:
                raise CommandError("Failed to delete webhook (see logs).")
            self.stdout.write(self.style.SUCCESS("✓ Webhook deleted."))
            return

        url = options["url"] or self._default_url()
        if not url:
            raise CommandError(
                "No --url given and BACKEND_URL is not set. Provide one of them."
            )
        if not url.startswith("https://"):
            raise CommandError("Telegram requires an HTTPS webhook URL.")

        secret = getattr(settings, "TELEGRAM_WEBHOOK_SECRET", "") or None
        if not secret:
            self.stdout.write(
                self.style.WARNING(
                    "TELEGRAM_WEBHOOK_SECRET is not set — registering without a "
                    "secret token. Set one for production."
                )
            )

        if set_webhook(url, secret_token=secret) is None:
            raise CommandError("Failed to set webhook (see logs).")

        self.stdout.write(self.style.SUCCESS(f"✓ Webhook registered at {url}"))

    def _default_url(self):
        base = getattr(settings, "BACKEND_URL", "").rstrip("/")
        if not base:
            return None
        return f"{base}{WEBHOOK_PATH}"

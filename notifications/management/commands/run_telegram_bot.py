"""
Management command: run_telegram_bot

Run the Telegram bot in long-polling mode for local development. In production
the bot is driven by a webhook (see ``set_telegram_webhook``); polling is just a
convenient way to exercise the same update-handling code without a public URL.

Polling and webhooks are mutually exclusive, so this command deletes any
registered webhook on startup.

Usage
-----
python manage.py run_telegram_bot
python manage.py run_telegram_bot --timeout 50
"""

import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Run the Telegram bot via long-polling (development only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
            help="Long-poll timeout in seconds (default: 30).",
        )

    def handle(self, *args, **options):
        if not getattr(settings, "TELEGRAM_BOT_TOKEN", ""):
            raise CommandError("TELEGRAM_BOT_TOKEN is not configured.")

        from notifications.telegram_bot import delete_webhook, get_updates
        from notifications.telegram_updates import handle_update

        # getUpdates returns 409 Conflict while a webhook is active — clear it.
        delete_webhook(drop_pending_updates=False)
        self.stdout.write(
            self.style.WARNING(
                "Deleted any active webhook. Long-polling for updates — press "
                "Ctrl-C to stop."
            )
        )

        timeout = options["timeout"]
        offset = None
        try:
            while True:
                updates = get_updates(offset=offset, timeout=timeout)
                for update in updates:
                    offset = update["update_id"] + 1
                    try:
                        handle_update(update)
                    except Exception:
                        logger.exception(
                            "Error handling update %s", update.get("update_id")
                        )
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("\nStopped."))

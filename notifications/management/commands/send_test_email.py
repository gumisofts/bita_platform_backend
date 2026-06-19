"""
Management command: send_test_email

Send a test email through the configured email backend. Useful for verifying
SMTP credentials (or, in DEBUG, that the console backend renders correctly).

Usage examples
--------------
# Send via the synchronous path (uses whatever EMAIL_BACKEND is configured)
python manage.py send_test_email --to you@example.com

# Custom subject/body
python manage.py send_test_email --to you@example.com \
    --subject "Hello" --message "It works!"

# Route through Celery (requires a running worker + broker)
python manage.py send_test_email --to you@example.com --async
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email to verify the email configuration."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            required=True,
            metavar="EMAIL",
            help="Recipient email address.",
        )
        parser.add_argument(
            "--subject",
            default="Bita test email",
            help="Email subject (default: 'Bita test email').",
        )
        parser.add_argument(
            "--message",
            default="This is a test email from the Bita platform.",
            help="Plain-text body (also rendered into the HTML template).",
        )
        parser.add_argument(
            "--async",
            dest="use_async",
            action="store_true",
            default=False,
            help="Dispatch via Celery (send_email_task.delay) instead of sending inline.",
        )

    def handle(self, *args, **options):
        to = options["to"]
        subject = options["subject"]
        message = options["message"]

        self.stdout.write(
            f"Backend: {self.style.SUCCESS(settings.EMAIL_BACKEND)}\n"
            f"From:    {settings.DEFAULT_FROM_EMAIL}\n"
            f"To:      {to}\n"
        )

        if options["use_async"]:
            from notifications.tasks import send_email_task

            try:
                result = send_email_task.delay(subject, message, [to])
            except Exception as exc:
                raise CommandError(f"Could not enqueue email task: {exc}")
            self.stdout.write(
                self.style.SUCCESS(f"✓ Queued email task (id: {result.id}).")
            )
            return

        from notifications.emails import send_email

        try:
            sent = send_email(subject, message, [to])
        except Exception as exc:
            raise CommandError(f"Failed to send email: {exc}")

        if sent:
            self.stdout.write(self.style.SUCCESS(f"✓ Sent {sent} message(s)."))
        else:
            self.stdout.write(
                self.style.WARNING("No message sent (no valid recipients?).")
            )

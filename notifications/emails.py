"""Low-level email rendering and delivery helpers.

This module knows how to turn a (subject, message) pair into a branded HTML
email and hand it to Django's configured email backend. Higher-level callers
should go through :mod:`notifications.service` (which adds async dispatch via
Celery) rather than calling :func:`send_email` directly.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

EMAIL_TEMPLATE = "email_template.html"


def render_email_html(subject, message):
    """Render the branded HTML body for an email."""
    return render_to_string(EMAIL_TEMPLATE, {"subject": subject, "message": message})


def send_email(subject, message, recipients, html_message=None):
    """Render and send an email through the configured backend.

    Args:
        subject: Email subject line.
        message: Plain-text body. Also used to render the default HTML template.
        recipients: A single address or an iterable of addresses.
        html_message: Optional pre-rendered HTML body. When omitted the shared
            ``email_template.html`` is rendered with ``subject``/``message``.

    Returns:
        The number of successfully delivered messages (0 if there were no
        valid recipients).
    """
    if isinstance(recipients, str):
        recipients = [recipients]
    recipients = [r for r in (recipients or []) if r]

    if not recipients:
        logger.warning("send_email called with no recipients (subject=%r)", subject)
        return 0

    if html_message is None:
        html_body = render_email_html(subject, message)
        text_body = message
    else:
        html_body = html_message
        text_body = message or strip_tags(html_message)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    email.attach_alternative(html_body, "text/html")
    sent = email.send(fail_silently=False)
    logger.info("Sent email %r to %d recipient(s)", subject, len(recipients))
    return sent

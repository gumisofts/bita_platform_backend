"""Telegram-username based employee invitations.

A business can invite someone by their Telegram @username before that person has
ever interacted with the bot. Because the Bot API cannot resolve a username to a
chat id, the invitation is stored with a normalised ``telegram_username`` and
delivered the moment the invitee is seen by the bot:

* If the username already belongs to a **linked** account (one with a
  ``telegram_id``), :func:`notify_user_if_linked` DMs them as soon as the
  invitation is created / resent.
* Otherwise the invitation waits until the person sends ``/start``, at which
  point :func:`deliver_pending_invitations` delivers every pending invite for
  their username with inline Accept / Reject buttons.

Accepting requires a linked Bita account (see :func:`process_invitation_callback`).
"""

import html
import logging

from django.core.exceptions import ValidationError
from django.utils import timezone

from business.models import EmployeeInvitation

logger = logging.getLogger(__name__)

# Looking up an invitation by a malformed id raises ValidationError (UUID parse)
# or ValueError depending on the backend; treat both as "not found".
_LOOKUP_ERRORS = (EmployeeInvitation.DoesNotExist, ValidationError, ValueError)


def normalize_telegram_username(value):
    """Return a username comparable across sources: no ``@``, lower-cased.

    Returns ``None`` for empty/blank input so it can be stored as NULL.
    """
    if not value:
        return None
    cleaned = str(value).strip().lstrip("@").lower()
    return cleaned or None


def build_invitation_message(invitation):
    """Return ``(html_text, reply_markup)`` for an invitation DM.

    The keyboard carries compact callback data (``inv:a:<id>`` / ``inv:r:<id>``)
    that :func:`process_invitation_callback` decodes; UUIDs keep it well under
    Telegram's 64-byte callback_data limit.
    """
    business_name = html.escape(invitation.business.name if invitation.business else "")
    role = invitation.role
    line = f"🏢 <b>{business_name}</b> has invited you to join"
    if role is not None and getattr(role, "role_name", None):
        line += f" as <b>{html.escape(role.role_name)}</b>"
    line += "."

    parts = [line]
    if invitation.branch is not None:
        parts.append(f"Branch: <b>{html.escape(invitation.branch.name)}</b>")
    parts.append("Would you like to accept?")

    text = "\n\n".join(parts)
    markup = {
        "inline_keyboard": [
            [
                {"text": "✅ Accept", "callback_data": f"inv:a:{invitation.id}"},
                {"text": "❌ Reject", "callback_data": f"inv:r:{invitation.id}"},
            ]
        ]
    }
    return text, markup


def pending_invitations_for_username(username):
    """Pending, unexpired invitations addressed to ``username``."""
    username = normalize_telegram_username(username)
    if not username:
        return EmployeeInvitation.objects.none()
    return EmployeeInvitation.objects.filter(
        telegram_username=username,
        status="pending",
        expires_at__gt=timezone.now(),
    ).select_related("business", "role", "branch")


def remember_telegram_username(telegram_id, username):
    """Persist the latest @username seen for a linked account.

    Keeps ``User.telegram_username`` current so future username-addressed
    invitations resolve to this account (and surface in the app's invitation
    list). No-op for users who haven't linked Telegram.
    """
    from accounts.models import User

    if not telegram_id:
        return
    username = normalize_telegram_username(username)
    User.objects.filter(telegram_id=telegram_id).exclude(
        telegram_username=username
    ).update(telegram_username=username)


def deliver_pending_invitations(telegram_id, username):
    """DM every pending invitation for ``username`` to ``telegram_id``.

    Called from the ``/start`` handler. Returns the number delivered.
    """
    from notifications.telegram_bot import _send_bot_message_sync

    delivered = 0
    for invitation in pending_invitations_for_username(username):
        text, markup = build_invitation_message(invitation)
        if _send_bot_message_sync(telegram_id, text, reply_markup=markup)["ok"]:
            delivered += 1
    if delivered:
        logger.info(
            "Delivered %d pending invitation(s) to telegram_id=%s on /start",
            delivered,
            telegram_id,
        )
    return delivered


def notify_user_if_linked(invitation):
    """DM the invitation immediately if its username belongs to a linked account.

    Returns ``True`` if a message was dispatched. Safe to call from a request
    path: sending is queued via Celery when enabled and never raises.
    """
    from accounts.models import User
    from notifications.telegram_bot import send_bot_message

    username = normalize_telegram_username(invitation.telegram_username)
    if not username:
        return False
    user = (
        User.objects.filter(telegram_username=username, telegram_id__isnull=False)
        .only("telegram_id")
        .first()
    )
    if not user:
        return False
    text, markup = build_invitation_message(invitation)
    send_bot_message(user.telegram_id, text, markup)
    return True


def process_invitation_callback(action, invitation_id, telegram_id, username):
    """Apply an Accept/Reject tapped in Telegram.

    ``action`` is ``"a"`` (accept) or ``"r"`` (reject). Returns a dict the
    dispatcher uses to reply::

        {"answer": <toast text>, "alert": <bool>, "text": <new message HTML|None>,
         "clear": <bool: drop the inline keyboard>}

    Acceptance requires a Bita account already linked to ``telegram_id``
    (decision: "require linking first"); unlinked users are asked to link in the
    app and the buttons are left in place so they can retry.
    """
    from accounts.models import User
    from business.signals import employee_invitation_status_changed

    try:
        invitation = EmployeeInvitation.objects.select_related(
            "business", "role", "branch"
        ).get(id=invitation_id)
    except _LOOKUP_ERRORS:
        return {
            "answer": "This invitation no longer exists.",
            "alert": False,
            "text": "This invitation is no longer available.",
            "clear": True,
        }

    business_name = html.escape(invitation.business.name if invitation.business else "")

    # Guard: must still be actionable.
    if invitation.is_expired:
        invitation.status = "expired"
        invitation.save(update_fields=["status"])
    if invitation.status != "pending":
        return {
            "answer": "This invitation is no longer available.",
            "alert": False,
            "text": f"This invitation to join <b>{business_name}</b> is no longer available.",
            "clear": True,
        }

    # Guard: the tapper must be the addressee.
    if normalize_telegram_username(username) != normalize_telegram_username(
        invitation.telegram_username
    ):
        return {
            "answer": "This invitation isn't addressed to your account.",
            "alert": True,
            "text": None,
            "clear": False,
        }

    if action == "a":
        user = User.objects.filter(telegram_id=telegram_id).first()
        if user is None:
            return {
                "answer": (
                    "Create or link your Bita account in the app first, then "
                    "tap Accept again."
                ),
                "alert": True,
                "text": None,
                "clear": False,
            }
        # Keep the stored handle current so the accept-signal resolves this user.
        normalized = normalize_telegram_username(username)
        if normalize_telegram_username(user.telegram_username) != normalized:
            user.telegram_username = normalized
            user.save(update_fields=["telegram_username"])

        invitation.status = "accepted"
        invitation.save(update_fields=["status"])
        employee_invitation_status_changed.send(
            sender=EmployeeInvitation, instance=invitation, status="accepted"
        )
        return {
            "answer": "You've joined the business!",
            "alert": False,
            "text": f"✅ You've joined <b>{business_name}</b>.",
            "clear": True,
        }

    if action == "r":
        invitation.status = "rejected"
        invitation.save(update_fields=["status"])
        return {
            "answer": "Invitation declined.",
            "alert": False,
            "text": f"You declined the invitation to join <b>{business_name}</b>.",
            "clear": True,
        }

    return {"answer": "Unknown action.", "alert": False, "text": None, "clear": False}

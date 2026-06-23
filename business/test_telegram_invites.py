"""Focused tests for Telegram-username based employee invitations."""

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from business.models import Business, Employee, EmployeeInvitation, Role
from business.telegram_invites import (
    normalize_telegram_username,
    pending_invitations_for_username,
    process_invitation_callback,
    remember_telegram_username,
)


class TelegramInviteTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create(phone_number="912000000", first_name="Owner")
        self.business = Business.objects.create(
            name="Acme", owner=self.owner, business_type="retail"
        )
        self.role = Role.objects.create(role_name="employee", business=self.business)

    def _invite(self, username="alice", status="pending", days=7):
        return EmployeeInvitation.objects.create(
            telegram_username=username,
            role=self.role,
            business=self.business,
            status=status,
            expires_at=timezone.now() + timezone.timedelta(days=days),
        )

    def test_normalize(self):
        self.assertEqual(normalize_telegram_username("@Alice"), "alice")
        self.assertEqual(normalize_telegram_username("  BOB "), "bob")
        self.assertIsNone(normalize_telegram_username("  "))
        self.assertIsNone(normalize_telegram_username(None))

    def test_pending_query_matches_normalized(self):
        inv = self._invite("alice")
        self.assertIn(inv, list(pending_invitations_for_username("@Alice")))
        self.assertEqual(list(pending_invitations_for_username("nobody")), [])

    def test_pending_query_excludes_expired(self):
        self._invite("alice", days=-1)
        self.assertEqual(list(pending_invitations_for_username("alice")), [])

    def test_remember_username_updates_linked_user(self):
        user = User.objects.create(
            phone_number="912111111", first_name="A", telegram_id=555
        )
        remember_telegram_username(555, "@Alice")
        user.refresh_from_db()
        self.assertEqual(user.telegram_username, "alice")

    def test_accept_without_linked_account_is_blocked(self):
        inv = self._invite("alice")
        result = process_invitation_callback("a", str(inv.id), 999, "alice")
        self.assertTrue(result["alert"])
        inv.refresh_from_db()
        self.assertEqual(inv.status, "pending")
        # No employee created for the invited role (the owner's own Employee,
        # auto-created with the business, is unrelated).
        self.assertFalse(
            Employee.objects.filter(business=self.business, role=self.role).exists()
        )

    def test_accept_with_linked_account_creates_employee(self):
        user = User.objects.create(
            phone_number="912222222",
            first_name="Alice",
            telegram_id=777,
            telegram_username="alice",
        )
        inv = self._invite("alice")
        result = process_invitation_callback("a", str(inv.id), 777, "@Alice")
        self.assertFalse(result["alert"])
        inv.refresh_from_db()
        self.assertEqual(inv.status, "accepted")
        self.assertTrue(
            Employee.objects.filter(user=user, business=self.business).exists()
        )

    def test_reject_marks_rejected(self):
        inv = self._invite("alice")
        result = process_invitation_callback("r", str(inv.id), 888, "alice")
        self.assertFalse(result["alert"])
        inv.refresh_from_db()
        self.assertEqual(inv.status, "rejected")

    def test_wrong_user_cannot_act(self):
        inv = self._invite("alice")
        result = process_invitation_callback("a", str(inv.id), 123, "mallory")
        self.assertTrue(result["alert"])
        inv.refresh_from_db()
        self.assertEqual(inv.status, "pending")

    def test_already_processed_is_reported(self):
        inv = self._invite("alice", status="accepted")
        result = process_invitation_callback("r", str(inv.id), 1, "alice")
        self.assertIn("no longer available", result["text"])

    def test_bad_invitation_id_is_handled(self):
        result = process_invitation_callback("a", "not-a-uuid", 1, "alice")
        self.assertIn("no longer available", result["text"])

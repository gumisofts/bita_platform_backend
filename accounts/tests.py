import hashlib
import hmac
import json
import time
from datetime import timedelta
from unittest import mock
from urllib.parse import unquote, urlencode

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core import mail, signing
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import *

TEST_BOT_TOKEN = "123456:test-bot-token"


def _sign_webapp(params, token=TEST_BOT_TOKEN):
    """Build a Telegram WebApp-signed querystring from decoded params."""
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    sig = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode({**params, "hash": sig})


def make_init_data(tg_id, first_name="Tele", last_name="Gram", token=TEST_BOT_TOKEN):
    user_json = json.dumps(
        {"id": tg_id, "first_name": first_name, "last_name": last_name}
    )
    return _sign_webapp(
        {"user": user_json, "auth_date": str(int(time.time()))}, token=token
    )


def make_contact_raw(tg_id, phone, first_name="Tele", token=TEST_BOT_TOKEN):
    contact_json = json.dumps(
        {"user_id": tg_id, "phone_number": phone, "first_name": first_name}
    )
    return _sign_webapp(
        {"contact": contact_json, "auth_date": str(int(time.time()))}, token=token
    )


def create_user(**kwargs):
    defaults = {
        "email": "test@example.com",
        "password": "StrongPass123!",
        "first_name": "Test User",
        "phone_number": "912345678",
    }
    defaults.update(kwargs)
    user = User.objects.create_user(**defaults)
    return user


class AccountsTestCase(APITestCase):

    def setUp(self):
        self.user = create_user()
        self.user.is_active = True
        self.user.is_phone_verified = True
        self.user.is_email_verified = True
        self.user.save()
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.auth_header = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    def test_register_user(self):
        url = reverse("auth-register")
        data = {
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "first_name": "NewUSer",
            "phone_number": "987654321",
        }
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_login_user(self):
        url = reverse("auth-login")
        data = {"email": self.user.email, "password": "StrongPass123!"}
        res = self.client.post(url, data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_password_change(self):
        url = reverse("auth-password-change")
        data = {"old_password": "StrongPass123!", "new_password": "NewStrongPass123!"}
        res = self.client.patch(url, data, **self.auth_header)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_token_verify(self):
        url = reverse("token-verify")
        res = self.client.post(url, {"token": self.token})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("user", res.data)

    def test_reset_password_request(self):
        url = reverse("auth-reset-request")
        res = self.client.post(url, {"email": self.user.email})
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_confirm_reset_password(self):
        url = reverse("auth-confirm-reset-password-request")
        data = {
            "code": "dummy",
            "new_password": "NewPass123!",
            "email": self.user.email,
        }
        res = self.client.post(url, data)
        self.assertIn(
            res.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]
        )

    def test_confirm_verification_code(self):
        url = reverse("auth-confirm-verification-code")
        res = self.client.post(url, {"code": "123456"})
        self.assertIn(
            res.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]
        )


@override_settings(TELEGRAM_BOT_TOKEN=TEST_BOT_TOKEN, FRONTEND_URL="https://app.test")
class TelegramLinkingTestCase(APITestCase):
    def setUp(self):
        # An existing Bita account a Telegram user may already own.
        self.existing = create_user(email="owner@example.com", phone_number="912345678")
        self.tg_id = 555000111

    def test_login_unlinked_returns_needs_link(self):
        url = reverse("auth-telegram-login")
        res = self.client.post(url, {"init_data": make_init_data(self.tg_id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "needs_link")
        self.assertNotIn("access", res.data)
        # No orphan account was created.
        self.assertFalse(User.objects.filter(telegram_id=self.tg_id).exists())

    def test_login_linked_returns_tokens(self):
        self.existing.telegram_id = self.tg_id
        self.existing.save(update_fields=["telegram_id"])
        url = reverse("auth-telegram-login")
        res = self.client.post(url, {"init_data": make_init_data(self.tg_id)})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "linked")
        self.assertIn("access", res.data)
        self.assertEqual(res.data["user"]["id"], str(self.existing.id))

    def test_contact_link_matches_phone(self):
        url = reverse("auth-telegram-link-contact")
        res = self.client.post(
            url,
            {
                "init_data": make_init_data(self.tg_id),
                # Telegram returns E.164; must match the bare stored phone.
                "contact_raw": make_contact_raw(self.tg_id, "+251912345678"),
            },
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.existing.refresh_from_db()
        self.assertEqual(self.existing.telegram_id, self.tg_id)
        self.assertTrue(self.existing.is_phone_verified)

    def test_contact_link_no_match(self):
        url = reverse("auth-telegram-link-contact")
        res = self.client.post(
            url,
            {
                "init_data": make_init_data(self.tg_id),
                "contact_raw": make_contact_raw(self.tg_id, "+251700000000"),
            },
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "no_phone_match")

    def test_contact_link_conflict(self):
        self.existing.telegram_id = 999999999  # already linked elsewhere
        self.existing.save(update_fields=["telegram_id"])
        url = reverse("auth-telegram-link-contact")
        res = self.client.post(
            url,
            {
                "init_data": make_init_data(self.tg_id),
                "contact_raw": make_contact_raw(self.tg_id, "+251912345678"),
            },
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_contact_replay_rejected(self):
        # Contact signed for a different Telegram user than the initData.
        url = reverse("auth-telegram-link-contact")
        res = self.client.post(
            url,
            {
                "init_data": make_init_data(self.tg_id),
                "contact_raw": make_contact_raw(123, "+251912345678"),
            },
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_request_existing_account(self):
        url = reverse("auth-telegram-link-email-request")
        res = self.client.post(
            url,
            {"init_data": make_init_data(self.tg_id), "email": "owner@example.com"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "link_sent")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            TelegramLinkRequest.objects.filter(user=self.existing).count(), 1
        )

    def test_email_request_no_account(self):
        url = reverse("auth-telegram-link-email-request")
        res = self.client.post(
            url,
            {"init_data": make_init_data(self.tg_id), "email": "ghost@example.com"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "no_account")
        self.assertEqual(len(mail.outbox), 0)

    @mock.patch("notifications.telegram_bot.send_bot_message")
    def test_email_create_new_account(self, mock_send):
        url = reverse("auth-telegram-link-email-create")
        res = self.client.post(
            url,
            {"init_data": make_init_data(self.tg_id), "email": "fresh@example.com"},
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "created")
        self.assertIn("access", res.data)
        user = User.objects.get(email="fresh@example.com")
        self.assertEqual(user.telegram_id, self.tg_id)
        mock_send.assert_called_once()
        # Credentials are DM'd to the same Telegram id that opened the app.
        self.assertEqual(mock_send.call_args.args[0], self.tg_id)

    def _make_link_token(self):
        link_request = TelegramLinkRequest.objects.create(
            telegram_id=self.tg_id,
            user=self.existing,
            email=self.existing.email,
            token="",
            expires_at=timezone.now() + timedelta(hours=1),
        )
        raw = signing.dumps(str(link_request.id), salt="accounts.telegram-link")
        link_request.token = make_password(raw)
        link_request.save(update_fields=["token"])
        return raw

    def test_connect_confirm_links_and_is_single_use(self):
        raw = self._make_link_token()
        url = reverse("auth-telegram-connect-confirm")

        res = self.client.post(url, {"token": raw})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["status"], "connected")
        self.existing.refresh_from_db()
        self.assertEqual(self.existing.telegram_id, self.tg_id)

        # Second use must be rejected (single-use).
        res2 = self.client.post(url, {"token": raw})
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_connect_confirm_emailed_token_works(self):
        # End-to-end: the token actually emailed by the request endpoint confirms.
        self.client.post(
            reverse("auth-telegram-link-email-request"),
            {"init_data": make_init_data(self.tg_id), "email": "owner@example.com"},
        )
        body = mail.outbox[0].body
        # Pull the token from the emailed link. It is percent-encoded in the URL;
        # the frontend's URLSearchParams decodes it before POSTing, so do the same.
        raw = unquote(body.split("token=")[1].split()[0].strip())
        res = self.client.post(reverse("auth-telegram-connect-confirm"), {"token": raw})
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.existing.refresh_from_db()
        self.assertEqual(self.existing.telegram_id, self.tg_id)

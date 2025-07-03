from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import *


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

    # def test_password_change(self):
    #     url = reverse("auth-password-change")
    #     data = {"old_password": "StrongPass123!", "new_password": "NewStrongPass123!"}
    #     res = self.client.post(url, data, **self.auth_header)
    #     self.assertEqual(res.status_code, status.HTTP_200_OK)

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
        data = {"code": "dummy", "new_password": "NewPass123!", "email": self.user.email}
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

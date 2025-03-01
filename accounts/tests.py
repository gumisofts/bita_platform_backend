from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    Address,
    Business,
    EmailChangeRequest,
    PhoneChangeRequest,
    Role,
)

User = get_user_model()


class UserCRUDTests(APITestCase):
    def setUp(self):
        # Create a user for update and delete tests
        self.user = User.objects.create_user(
            email="original@example.com",
            phone_number="912345678",
            first_name="Original",
            last_name="User",
            password="origpassword",
        )
        self.user_url = reverse("user-detail", args=[self.user.pk])
        self.user_list_url = reverse("user-list")

    def test_create_user(self):
        # Test that a user can be created with a POST request
        payload = {
            "email": "newuser@example.com",
            "phone_number": "712345678",
            "first_name": "New",
            "last_name": "User",
            "password": "newpassword123",
        }
        response = self.client.post(self.user_list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        created_user = User.objects.get(pk=response.data["id"])
        self.assertEqual(created_user.email, payload["email"])
        self.assertEqual(created_user.phone_number, payload["phone_number"])
        self.assertEqual(created_user.first_name, payload["first_name"])
        self.assertEqual(created_user.last_name, payload["last_name"])
        self.assertTrue(created_user.check_password(payload["password"]))
        # Default fields
        self.assertTrue(created_user.is_active)
        self.assertFalse(created_user.is_superuser)
        self.assertFalse(created_user.is_staff)

    def test_edit_user_restricted_fields(self):
        # Authenticate as the user to perform update
        self.client.force_authenticate(user=self.user)
        # Attempt to update allowed field (first_name) and disallowed fields.
        payload = {
            "first_name": "UpdatedName",
            "email": "changed@example.com",
            "phone_number": "712345678",
            "password": "hackedpwd",
            "is_superuser": True,
            "is_staff": True,
        }
        response = self.client.patch(self.user_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Refresh user instance and check fields
        self.user.refresh_from_db()
        # Allowed field
        self.assertEqual(self.user.first_name, "UpdatedName")
        # Disallowed fields remain unchanged
        self.assertEqual(self.user.email, "original@example.com")
        self.assertEqual(self.user.phone_number, "912345678")
        # Password remains unchanged
        self.assertTrue(self.user.check_password("origpassword"))
        # is_superuser and is_staff remain unchanged
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.is_staff)

    def test_delete_user_sets_inactive(self):
        # Authenticate as the user to perform delete
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.user_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # The user should still exist but is_active should be False
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)


class PhoneChangeRequestTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            phone_number="912345678",
            first_name="Test",
            last_name="User",
            password="testpass",
        )
        # URL names used in urls.py for phone change endpoints
        self.phone_change_request_url = reverse("phone-change")
        self.phone_change_confirm_url_name = (
            "phone-change-confirm"  # expects uidb64 and token as args
        )

    @patch("accounts.serializers.requests.request")
    def test_create_phone_change_request(self, mock_request):
        # Configure the mock to return a successful response.
        mock_request.return_value.status_code = 200
        self.client.force_authenticate(user=self.user)
        payload = {"new_phone": "712345678"}
        response = self.client.post(
            self.phone_change_request_url, payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertIn("sent", response.data["detail"].lower())
        # Verify a PhoneChangeRequest was created in the db
        request_obj = PhoneChangeRequest.objects.filter(user=self.user).first()
        self.assertIsNotNone(request_obj)
        self.assertEqual(request_obj.new_phone, payload["new_phone"])

    @patch("accounts.serializers.requests.request")
    def test_confirm_phone_change_request(self, mock_request):
        """
        Test that providing a valid uid and token updates the
        user's phone number
        and deletes the PhoneChangeRequest.
        """
        self.client.force_authenticate(user=self.user)
        payload = {"new_phone": "712345678"}
        # Create the phone change request
        self.client.post(self.phone_change_request_url, payload, format="json")
        # Prepare uidb64 and token (using the same default_token_generator
        # as in the views)
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse(
            self.phone_change_confirm_url_name,
            args=[uidb64, token],
        )
        response = self.client.post(confirm_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify that the user's phone number was updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, payload["new_phone"])
        # Verify that the PhoneChangeRequest is removed
        self.assertFalse(
            PhoneChangeRequest.objects.filter(user=self.user).exists(),
        )

    @patch("accounts.serializers.requests.request")
    def test_confirm_phone_change_request_invalid_token(self, mock_request):
        """
        Test that providing an invalid token returns an error.
        """
        self.client.force_authenticate(user=self.user)
        payload = {"new_phone": "712345678"}
        self.client.post(self.phone_change_request_url, payload, format="json")
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        invalid_token = "invalidtoken"
        confirm_url = reverse(
            self.phone_change_confirm_url_name, args=[uidb64, invalid_token]
        )
        response = self.client.post(confirm_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("invalid", response.data["detail"].lower())

    @patch("accounts.serializers.requests.request")
    def test_confirm_phone_change_request_expired(self, mock_request):
        """
        Test that if the PhoneChangeRequest has expired, confirmation fails.
        """
        self.client.force_authenticate(user=self.user)
        payload = {"new_phone": "712345678"}
        self.client.post(self.phone_change_request_url, payload, format="json")
        # Manually expire the PhoneChangeRequest
        phone_request = PhoneChangeRequest.objects.filter(
            user=self.user,
        ).first()
        phone_request.expires_at = timezone.now() - timezone.timedelta(
            minutes=1,
        )
        phone_request.save()
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse(
            self.phone_change_confirm_url_name,
            args=[uidb64, token],
        )
        response = self.client.post(confirm_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "no valid phone change request",
            response.data["detail"].lower(),
        )


class EmailChangeRequestTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            phone_number="912345678",
            first_name="Test",
            last_name="User",
            password="testpass",
        )
        # URL names should match those defined in your accounts/urls.py
        self.email_change_request_url = reverse("email-change")
        self.email_change_confirm_url_name = (
            "email-change-confirm"  # expects uidb64 and token as args
        )

    @patch("accounts.serializers.requests.request")
    def test_create_email_change_request(self, mock_request):
        # Configure the mock to return a successful response.
        mock_request.return_value.status_code = 200
        self.client.force_authenticate(user=self.user)
        payload = {"new_email": "newuser@example.com"}
        response = self.client.post(
            self.email_change_request_url, payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertIn("sent", response.data["detail"].lower())
        request_obj = EmailChangeRequest.objects.filter(user=self.user).first()
        self.assertIsNotNone(request_obj)
        self.assertEqual(request_obj.new_email, payload["new_email"])

    @patch("accounts.serializers.requests.request")
    def test_confirm_email_change_request(self, mock_request):
        # Even though the email send happens in
        # creation, it is already mocked above.
        self.client.force_authenticate(user=self.user)
        payload = {"new_email": "newuser@example.com"}
        self.client.post(self.email_change_request_url, payload, format="json")
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse(
            self.email_change_confirm_url_name,
            args=[uidb64, token],
        )
        response = self.client.post(confirm_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, payload["new_email"])
        self.assertFalse(
            EmailChangeRequest.objects.filter(user=self.user).exists(),
        )

    @patch("accounts.serializers.requests.request")
    def test_confirm_email_change_request_invalid_token(self, mock_request):
        self.client.force_authenticate(user=self.user)
        payload = {"new_email": "newuser@example.com"}
        self.client.post(self.email_change_request_url, payload, format="json")
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        invalid_token = "invalidtoken"
        confirm_url = reverse(
            self.email_change_confirm_url_name, args=[uidb64, invalid_token]
        )
        response = self.client.post(confirm_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("invalid", response.data["detail"].lower())

    @patch("accounts.serializers.requests.request")
    def test_confirm_email_change_request_expired(self, mock_request):
        self.client.force_authenticate(user=self.user)
        payload = {"new_email": "newuser@example.com"}
        self.client.post(self.email_change_request_url, payload, format="json")
        email_request = EmailChangeRequest.objects.filter(
            user=self.user,
        ).first()
        email_request.expires_at = timezone.now() - timezone.timedelta(
            minutes=1,
        )
        email_request.save()
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse(
            self.email_change_confirm_url_name,
            args=[uidb64, token],
        )
        response = self.client.post(confirm_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "no valid email change request",
            response.data["detail"].lower(),
        )


class PasswordResetTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="resetuser@example.com",
            phone_number="912345678",
            first_name="Reset",
            last_name="User",
            password="oldpassword123",
        )
        # Assuming these URL names are defined in accounts/urls.py
        self.password_reset_url = reverse("password-reset")
        self.password_reset_confirm_url_name = "password-reset-confirm"

    @patch("accounts.serializers.requests.request")
    def test_password_reset_valid(self, mock_request):
        """
        Test that a valid password reset request returns 200 and
        triggers the external request.
        """
        mock_request.return_value.status_code = 200
        payload = {"email": self.user.email}
        response = self.client.post(
            self.password_reset_url,
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        mock_request.assert_called_once()

    def test_password_reset_invalid_email(self):
        """
        Test that a password reset with a non-existent email returns 400.
        """
        payload = {"email": "nonexistent@example.com"}
        response = self.client.post(
            self.password_reset_url,
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "does not exist",
            response.data.get("email", [""])[0].lower(),
        )

    def test_password_reset_confirm_valid(self):
        """
        Test that providing a valid uid, token,
        and new password resets the password.
        """
        # Prepare uid and token as in the PasswordResetConfirmView
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse(
            self.password_reset_confirm_url_name, args=[uidb64, token]
        )
        payload = {
            "password": "newsecurepassword",
            "password_confirm": "newsecurepassword",
        }
        response = self.client.post(confirm_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify that the user's password was updated
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newsecurepassword"))

    def test_password_reset_confirm_invalid_token(self):
        """
        Test that an invalid token returns an error.
        """
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        invalid_token = "invalidtoken"
        confirm_url = reverse(
            self.password_reset_confirm_url_name, args=[uidb64, invalid_token]
        )
        payload = {
            "new_password": "newpassword",
            "new_password_confirm": "newpassword",
        }
        response = self.client.post(confirm_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("invalid", response.data.get("detail", "").lower())


class LoginTests(APITestCase):
    def setUp(self):
        self.password = "testpassword123"
        self.user = User.objects.create_user(
            email="loginuser@example.com",
            phone_number="912345678",
            first_name="Login",
            last_name="User",
            password=self.password,
        )
        # This URL name should be defined in your accounts/urls.py
        self.login_url = reverse("token_obtain_pair")

    def test_login_with_email(self):
        """
        Test that a user can log in using their email address.
        """
        payload = {"identifier": self.user.email, "password": self.password}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Optionally, check for presence of a token or
        # success detail in response
        self.assertTrue("access" in response.data or "detail" in response.data)

    def test_login_with_phone_number(self):
        """
        Test that a user can log in using their phone number.
        """
        payload = {
            "identifier": self.user.phone_number,
            "password": self.password,
        }
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Optionally, check for the token or success detail in response
        self.assertTrue("access" in response.data or "detail" in response.data)

    def test_login_invalid_credentials(self):
        """
        Test that login fails with invalid credentials.
        """
        payload = {"identifier": self.user.email, "password": "wrongpassword"}
        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class EmployeeInvitationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            phone_number="912345678",
            first_name="Test",
            last_name="User",
            password="testpass",
        )
        self.role = Role.objects.create(role_name="Sales", role_code=1)
        self.business = Business.objects.create(
            name="Test Business",
            owner=self.user,
            business_type=1,
            address=Address.objects.create(
                lat=0.0,
                lng=0.0,
                plus_code=123456,
                sublocality="Suburb",
                locality="City",
                admin_1="State",
                admin_2="Region",
                country="Country",
            ),
        )
        self.invitation_url = reverse("employee-invitation")

    @patch("accounts.serializers.requests.request")
    def test_create_employee_invitation(self, mock_request):
        """
        Test that a user can send an invitation to another user.
        """
        mock_request.return_value.status_code = 200
        self.client.force_authenticate(user=self.user)
        payload = {
            "user_id": self.user.id,
            "business_id": self.business.id,
            "role_id": self.role.id,
        }
        response = self.client.post(
            self.invitation_url,
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("detail", response.data)
        self.assertIn("sent", response.data["detail"].lower())

    @patch("accounts.serializers.requests.request")
    def test_create_employee_invitation_invalid_role(self, mock_request):
        """
        Test that an invitation with an invalid role returns an error.
        """
        mock_request.return_value.status_code = 200
        self.client.force_authenticate(user=self.user)
        payload = {
            "email": "user@example.com",
            "role": 999,
            "business": self.business.pk,
        }
        response = self.client.post(
            self.invitation_url,
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.serializers.requests.request")
    def test_create_employee_invitation_invalid_business(self, mock_request):
        """
        Test that an invitation with an invalid business returns an error.
        """
        mock_request.return_value.status_code = 200
        self.client.force_authenticate(user=self.user)
        payload = {
            "email": "user@example.com",
            "role": self.role.pk,
            "business": 999,
        }
        response = self.client.post(
            self.invitation_url,
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.serializers.requests.request")
    def test_create_employee_invitation_invalid_email(self, mock_request):
        """
        Test that an invitation with an invalid email returns an error.
        """
        mock_request.return_value.status_code = 200
        self.client.force_authenticate(user=self.user)
        payload = {
            "email": "invalidemail",
            "role": self.role.pk,
            "business": self.business.pk,
        }
        response = self.client.post(
            self.invitation_url,
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_employee_invitation_confirm_valid(self):
        """
        Test that providing a valid uid, token, business, and role
        creates an Employee instance.
        """
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        confirm_url = reverse(
            "employee-invitation-confirm",
            args=[self.business.pk, self.role.pk, uidb64, token],
        )
        response = self.client.post(confirm_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify that the Employee instance was created
        employee = self.user.employee_set.get()
        self.assertEqual(employee.role, self.role)
        self.assertEqual(employee.business, self.business)

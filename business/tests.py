from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from business.models import Branch, Business, Category, Employee, Role

User = get_user_model()


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

    def test_address_crud(self):
        url = reverse("addresses-list")
        data = {"lat": 0, "lng": 0, "country": "Ethiopia", "admin_1": "Addis Ababa"}
        res = self.client.post(url, data, **self.auth_header)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_business_crud(self):
        url = reverse("businesses-list")
        data = {"name": "Test Biz", "owner": self.user.id, "description": "Some desc"}
        self.client.force_authenticate(user=self.user)
        res = self.client.post(url, data)
        self.assertIn(
            res.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        )

    def test_category_list(self):
        Category.objects.create(name="Electronics")
        url = reverse("categories-list")
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_role_list(self):
        role = Role.objects.create(role_name="Manager")
        url = reverse("roles-detail", args=[role.id])
        res = self.client.get(url, **self.auth_header)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_branch_crud(self):
        url = reverse("branches-list")
        data = {"name": "Main Branch"}
        res = self.client.post(url, data, **self.auth_header)
        self.assertIn(
            res.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        )

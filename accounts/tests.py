from urllib.parse import urlencode
from environs import Env
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from .models import (
    EmployeeBusiness,
    User,
    Supplier,
    Customer,
    Business,
    EmployeeInvitation,
)
import json
from unittest.mock import patch


env = Env()
env.read_env()

User = get_user_model()


class BaseAPITestCase(APITestCase):
    def get_jwt_token(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)


class UserCRUDAPITestCase(BaseAPITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            phone="912345678",
            password="adminpass123",
        )
        self.regular_user = User.objects.create_user(
            email="regularuser@example.com",
            phone="912345679",
            password="userpass123",
        )
        self.user_data = {
            "email": "testuser@example.com",
            "phone": "912345432",
            "password": "testpass123",
        }

    def test_create_user(self):
        """Test creating a new user."""
        url = reverse("user-list")
        response = self.client.post(url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 3)

    def test_admin_can_list_users(self):
        token = self.get_jwt_token(self.admin_user)
        url = reverse("user-list")
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_regular_user_cannot_list_users(self):
        token = self.get_jwt_token(self.regular_user)
        url = reverse("user-list")
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_update_own_user(self):
        token = self.get_jwt_token(self.regular_user)
        url = reverse("user-detail", args=[self.regular_user.id])
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        response = self.client.patch(url, {"email": "newemail@example.com"}, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.email, "newemail@example.com")

    def test_admin_can_update_any_user(self):
        token = self.get_jwt_token(self.admin_user)
        url = reverse("user-detail", args=[self.regular_user.id])
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.patch(
            url, {"email": "adminupdated@example.com"}, **headers
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.email, "adminupdated@example.com")

    def test_non_owner_cannot_update_user(self):
        another_user = User.objects.create_user(
            email="anotheruser@example.com",
            phone="912345680",
            password="anotherpass123",
        )
        token = self.get_jwt_token(self.regular_user)
        url = reverse("user-detail", args=[another_user.id])
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.patch(
            url, {"email": "unauthorized@example.com"}, **headers
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_own_user(self):
        token = self.get_jwt_token(self.regular_user)
        url = reverse("user-detail", args=[self.regular_user.id])
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.delete(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(id=self.regular_user.id).exists())

    def test_admin_can_delete_any_user(self):
        token = self.get_jwt_token(self.admin_user)
        url = reverse("user-detail", args=[self.regular_user.id])
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.delete(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(id=self.regular_user.id).exists())

    def test_non_owner_cannot_delete_user(self):
        another_user = User.objects.create_user(
            email="anotheruser@example.com",
            phone="912345680",
            password="anotherpass123",
        )
        token = self.get_jwt_token(self.regular_user)
        url = reverse("user-detail", args=[another_user.id])
        headers = {
            "Authorization": f"Bearer {token}",
        }
        response = self.client.delete(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_user_cannot_list_users(self):
        url = reverse("user-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_user_cannot_retrieve_user(self):
        user = User.objects.get(email="admin@example.com")
        url = reverse("user-detail", args=[user.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_user_cannot_update_user(self):
        user = User.objects.get(email="admin@example.com")
        url = reverse("user-detail", args=[user.id])
        data = {
            "email": "admin_updated@example.com",
            "phone": "987654321",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_user_cannot_delete_user(self):
        user = User.objects.get(email="admin@example.com")
        url = reverse("user-detail", args=[user.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_change(self):
        token = self.get_jwt_token(self.regular_user)
        url = reverse("password-change")
        data = {
            "old_password": "userpass123",
            "new_password": "newpass123",
            "new_password_confirm": "newpass123",
        }
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.put(url, data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.check_password("newpass123"))

    def test_password_reset_confirm(self):
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator

        uid = urlsafe_base64_encode(force_bytes(self.regular_user.pk))
        token = default_token_generator.make_token(self.regular_user)
        url = reverse("password-reset-confirm", args=[uid, token])
        data = {
            "password": "newpass123",
            "password_confirm": "newpass123",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.regular_user.refresh_from_db()
        self.assertTrue(self.regular_user.check_password("newpass123"))

    def test_authentication_via_phone(self):
        url = reverse("token_obtain_pair")
        data = {
            "identifier": self.regular_user.phone,
            "password": "userpass123",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_authentication_via_email(self):
        url = reverse("token_obtain_pair")
        data = {
            "identifier": self.regular_user.email,
            "password": "userpass123",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)


class SupplierCRUDAPITestCase(BaseAPITestCase):
    def setUp(self):
        self.owner_user = User.objects.create_user(
            email="owner@example.com",
            phone="912345679",
            password="ownerpass123",
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            phone="912345678",
            password="adminpass123",
        )
        self.supplier_data = {
            "name": "Supplier 1",
            "phone": "912345678",
            "email": "supplier1@example.com",
            "address": "Supplier 1 address",
        }
        self.business = Business.objects.create(
            name="Supplier Business",
            address="123 Supplier Road",
            category="Services",
            owner=self.owner_user,
        )
        self.admin_eb = EmployeeBusiness.objects.create(
            employee=self.admin_user,
            role=2,
            business=self.business,
            created_by=self.owner_user,
        )
        self.owner_eb = EmployeeBusiness.objects.create(
            employee=self.owner_user,
            role=1,
            business=self.business,
            created_by=self.owner_user,
        )

    def test_create_supplier(self):
        token = self.get_jwt_token(self.admin_user)
        params = {"business": self.business.id}
        url = f"{reverse('supplier-list')}?{urlencode(params)}"
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.post(url, self.supplier_data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Supplier.objects.count(), 1)

    def test_admin_can_list_suppliers(self):
        token = self.get_jwt_token(self.admin_user)
        url = reverse("supplier-list")
        query_params = {"business": self.business.id}
        url = f"{url}?{urlencode(query_params)}"
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_retrieve_supplier(self):
        token = self.get_jwt_token(self.admin_user)
        supplier = Supplier.objects.create(business=self.business, **self.supplier_data)
        url = reverse("supplier-detail", args=[supplier.id])
        query_params = {"business": self.business.id}
        url = f"{url}?{urlencode(query_params)}"
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_update_supplier(self):
        token = self.get_jwt_token(self.admin_user)
        supplier = Supplier.objects.create(business=self.business, **self.supplier_data)
        url = reverse("supplier-detail", args=[supplier.id])
        query_params = {"business": self.business.id}
        url = f"{url}?{urlencode(query_params)}"
        data = {
            "name": "Supplier 2",
            "phone": "912345679",
            "email": "supplier2@example.com",
            "address": "Supplier 2 address",
        }
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.put(url, data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        supplier.refresh_from_db()
        self.assertEqual(supplier.name, "Supplier 2")

    def test_admin_can_delete_supplier(self):
        token = self.get_jwt_token(self.admin_user)
        supplier = Supplier.objects.create(business=self.business, **self.supplier_data)
        url = reverse("supplier-detail", args=[supplier.id])
        query_params = {"business": self.business.id}
        url = f"{url}?{urlencode(query_params)}"
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.delete(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Supplier.objects.filter(id=supplier.id).exists())

    def test_unauthorized_user_cannot_list_suppliers(self):
        url = reverse("supplier-list")

        response = self.client.get(
            url,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_user_cannot_retrieve_supplier(self):
        supplier = Supplier.objects.create(**self.supplier_data)
        url = reverse("supplier-detail", args=[supplier.id])

        response = self.client.get(
            url,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_user_cannot_update_supplier(self):
        supplier = Supplier.objects.create(**self.supplier_data)
        url = reverse("supplier-detail", args=[supplier.id])
        data = {
            "name": "Unauthorized Supplier",
            "phone": "912345679",
            "email": "unauth@example.com",
            "address": "Unauthorized Supplier address",
        }

        response = self.client.put(
            url,
            data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_user_cannot_delete_supplier(self):
        supplier = Supplier.objects.create(**self.supplier_data)
        url = reverse("supplier-detail", args=[supplier.id])

        response = self.client.delete(
            url,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CustomerCRUDAPITestCase(BaseAPITestCase):
    def setUp(self):
        self.owner_user = User.objects.create_user(
            email="owner@example.com",
            phone="912345679",
            password="ownerpass123",
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            phone="912345678",
            password="adminpass123",
        )
        self.business = Business.objects.create(
            name="Supplier Business",
            address="123 Supplier Road",
            category="Services",
            owner=self.owner_user,
        )
        self.admin_eb = EmployeeBusiness.objects.create(
            employee=self.admin_user,
            role=2,
            business=self.business,
            created_by=self.owner_user,
        )
        self.owner_eb = EmployeeBusiness.objects.create(
            employee=self.owner_user,
            role=1,
            business=self.business,
            created_by=self.owner_user,
        )
        self.customer_data = {
            "first_name": "Customer",
            "last_name": "1",
            "phone": "912345678",
            "email": "customer1@example.com",
            "address": "Customer 1 address",
        }

    def test_create_customer(self):
        token = self.get_jwt_token(self.admin_user)
        url = reverse("customer-list")
        params = {"business": self.business.id}
        url = f"{url}?{urlencode(params)}"
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.post(url, self.customer_data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Customer.objects.count(), 1)

    def test_admin_can_list_customers(self):
        token = self.get_jwt_token(self.admin_user)
        url = reverse("customer-list")
        params = {"business": self.business.id}
        url = f"{url}?{urlencode(params)}"
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_retrieve_customer(self):
        token = self.get_jwt_token(self.admin_user)
        customer = Customer.objects.create(business=self.business, **self.customer_data)
        url = reverse("customer-detail", args=[customer.id])
        params = {"business": self.business.id}
        url = f"{url}?{urlencode(params)}"
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_admin_can_update_customer(self):
        token = self.get_jwt_token(self.admin_user)
        customer = Customer.objects.create(business=self.business, **self.customer_data)
        url = reverse("customer-detail", args=[customer.id])
        params = {"business": self.business.id}
        url = f"{url}?{urlencode(params)}"
        data = {
            "first_name": "Customer",
            "last_name": "2",
            "phone": "912345679",
            "email": "customer2@example.com",
            "address": "Customer 2 address",
        }
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.put(url, data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        customer.refresh_from_db()
        self.assertEqual(customer.last_name, "2")

    def test_admin_can_delete_customer(self):
        token = self.get_jwt_token(self.admin_user)
        customer = Customer.objects.create(business=self.business, **self.customer_data)
        url = reverse("customer-detail", args=[customer.id])
        params = {"business": self.business.id}
        url = f"{url}?{urlencode(params)}"
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.delete(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Customer.objects.filter(id=customer.id).exists())

    def test_unauthorized_user_cannot_list_customers(self):
        url = reverse("customer-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_user_cannot_retrieve_customer(self):
        customer = Customer.objects.create(**self.customer_data)
        url = reverse("customer-detail", args=[customer.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_user_cannot_update_customer(self):
        customer = Customer.objects.create(**self.customer_data)
        url = reverse("customer-detail", args=[customer.id])
        data = {
            "first_name": "Unauthorized Customer",
            "last_name": "1",
            "phone": "912345679",
            "email": "unauth@example.com",
            "address": "Unauthorized Customer address",
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthorized_user_cannot_delete_customer(self):
        customer = Customer.objects.create(**self.customer_data)
        url = reverse("customer-detail", args=[customer.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CustomerSupplierPermissionTestCase(BaseAPITestCase):
    def setUp(self):
        self.owner_user = User.objects.create_user(
            email="owner@example.com",
            phone="912345679",
            password="ownerpass123",
        )
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            phone="912345678",
            password="adminpass123",
        )
        self.regular_user = User.objects.create_user(
            email="regular@example.com",
            phone="912345673",
            password="userpass123",
        )
        self.customer_data = {
            "first_name": "Customer",
            "last_name": "Test",
            "phone": "912345678",
            "email": "customer@example.com",
            "address": "Customer Address",
        }
        self.supplier_data = {
            "name": "Supplier Test",
            "phone": "912345678",
            "email": "supplier@example.com",
            "address": "Supplier Address",
        }
        self.business = Business.objects.create(
            name="Test Business",
            address="123 Test Lane",
            category="Retail",
            owner=self.owner_user,
        )
        EmployeeBusiness.objects.create(
            employee=self.owner_user,
            role=1,
            business=self.business,
            created_by=self.owner_user,
        )
        EmployeeBusiness.objects.create(
            employee=self.admin_user,
            role=2,
            business=self.business,
            created_by=self.owner_user,
        )
        EmployeeBusiness.objects.create(
            employee=self.regular_user,
            role=3,
            business=self.business,
            created_by=self.owner_user,
        )

    # --- Customer endpoint tests ---

    def test_owner_can_update_own_customer(self):
        token = self.get_jwt_token(self.owner_user)
        customer = Customer.objects.create(
            business=self.business, created_by=self.regular_user, **self.customer_data
        )
        url = reverse("customer-detail", args=[customer.id])
        params = {"business": self.business.id}
        url = f"{url}?{urlencode(params)}"
        data = {
            "first_name": "Updated",
            "last_name": customer.last_name,
            "phone": customer.phone,
            "email": customer.email,
            "address": customer.address,
        }
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.patch(url, data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        customer.refresh_from_db()
        self.assertEqual(customer.first_name, "Updated")

    def test_non_owner_cannot_update_customer(self):
        customer = Customer.objects.create(
            created_by=self.owner_user, **self.customer_data
        )
        token = self.get_jwt_token(self.regular_user)
        url = reverse("customer-detail", args=[customer.id])
        params = {"business": self.business.id}
        url = f"{url}?{urlencode(params)}"
        data = {"first_name": "Hacked"}
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.patch(url, data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_any_customer(self):
        customer = Customer.objects.create(
            business=self.business, created_by=self.regular_user, **self.customer_data
        )
        token = self.get_jwt_token(self.admin_user)
        url = reverse("customer-detail", args=[customer.id])
        params = {"business": self.business.id}
        url = f"{url}?{urlencode(params)}"
        data = {"first_name": "AdminUpdated"}
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.patch(url, data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Supplier endpoint tests ---

    def test_owner_can_update_own_supplier(self):
        token = self.get_jwt_token(self.owner_user)
        supplier = Supplier.objects.create(
            business=self.business, created_by=self.regular_user, **self.supplier_data
        )
        url = reverse("supplier-detail", args=[supplier.id])
        query_params = {"business": self.business.id}
        url = f"{url}?{urlencode(query_params)}"
        data = {
            "name": "Updated Supplier",
            "phone": supplier.phone,
            "email": supplier.email,
            "address": supplier.address,
        }
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.patch(url, data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        supplier.refresh_from_db()
        self.assertEqual(supplier.name, "Updated Supplier")

    def test_non_owner_cannot_update_supplier(self):
        owner = User.objects.create_user(
            email="owner2@example.com",
            phone="912345222",
            password="ownerpass222",
        )
        supplier = Supplier.objects.create(
            business=self.business, created_by=owner, **self.supplier_data
        )
        token = self.get_jwt_token(self.regular_user)
        url = reverse("supplier-detail", args=[supplier.id])
        query_params = {"business": self.business.id}
        url = f"{url}?{urlencode(query_params)}"
        data = {"name": "Hacked Supplier"}
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.patch(url, data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_update_any_supplier(self):
        supplier = Supplier.objects.create(
            business=self.business, created_by=self.regular_user, **self.supplier_data
        )
        token = self.get_jwt_token(self.admin_user)
        url = reverse("supplier-detail", args=[supplier.id])
        query_params = {"business": self.business.id}
        url = f"{url}?{urlencode(query_params)}"
        data = {"name": "Admin Updated Supplier"}
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        response = self.client.patch(url, data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class JWTTokenVerifyTestCase(BaseAPITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            phone="912345678",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

    def test_valid_token_verification(self):
        token = self.get_jwt_token(self.user)
        url = reverse("token_verify")
        data = {"token": token}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"]["email"], self.user.email)

    def test_invalid_token_verification(self):
        url = reverse("token_verify")
        data = {"token": "invalidtoken"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class BusinessCRUDAPITestCase(BaseAPITestCase):
    def setUp(self):
        # Create users for testing
        self.admin_user = User.objects.create_superuser(
            email="admin@example.com",
            phone="912345678",
            password="adminpass123",
        )
        self.owner_user = User.objects.create_user(
            email="owner@example.com",
            phone="912345679",
            password="ownerpass123",
        )
        self.regular_user = User.objects.create_user(
            email="regular@example.com",
            phone="912345680",
            password="userpass123",
        )
        # Create a business by owner_user
        self.business_data = {
            "name": "Test Business",
            "address": "123 Test Lane",
            "category": "Retail",
            "owner": self.owner_user,
        }
        self.business = Business.objects.create(**self.business_data)

    def get_auth_headers(self, user):
        token = self.get_jwt_token(user)
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        return headers

    def test_admin_can_list_businesses(self):
        url = reverse("business-list")
        headers = self.get_auth_headers(self.admin_user)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Expect at least one business in the list
        self.assertGreaterEqual(len(response.data), 1)

    def test_owner_can_retrieve_business(self):
        url = reverse("business-detail", args=[self.business.id])
        headers = self.get_auth_headers(self.owner_user)
        response = self.client.get(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("name"), self.business_data["name"])

    def test_owner_can_update_business(self):
        url = reverse("business-detail", args=[self.business.id])
        headers = self.get_auth_headers(self.owner_user)
        data = {"name": "Updated Business Name"}
        response = self.client.patch(url, data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.business.refresh_from_db()
        self.assertEqual(self.business.name, data["name"])

    def test_non_owner_cannot_update_business(self):
        url = reverse("business-detail", args=[self.business.id])
        headers = self.get_auth_headers(self.regular_user)
        data = {"name": "Should Not Update"}
        response = self.client.patch(url, data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_update_business(self):
        url = reverse("business-detail", args=[self.business.id])
        headers = self.get_auth_headers(self.admin_user)
        data = {"address": "456 Admin Ave"}
        response = self.client.patch(url, data, format="json", **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.business.refresh_from_db()
        self.assertEqual(self.business.address, data["address"])

    def test_owner_can_delete_business(self):
        # Create a new business to test deletion
        business = Business.objects.create(
            name="Delete Test",
            address="Delete Address",
            category="Service",
            owner=self.owner_user,
        )
        url = reverse("business-detail", args=[business.id])
        headers = self.get_auth_headers(self.owner_user)
        response = self.client.delete(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Business.objects.filter(id=business.id).exists())

    def test_admin_can_delete_business(self):
        # Create a new business with owner_user as creator
        business = Business.objects.create(
            name="Admin Delete",
            address="Admin Delete Address",
            category="Tech",
            owner=self.owner_user,
        )
        url = reverse("business-detail", args=[business.id])
        headers = self.get_auth_headers(self.admin_user)
        response = self.client.delete(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Business.objects.filter(id=business.id).exists())

    def test_non_owner_cannot_delete_business(self):
        url = reverse("business-detail", args=[self.business.id])
        headers = self.get_auth_headers(self.regular_user)
        response = self.client.delete(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Business should still exist
        self.assertTrue(Business.objects.filter(id=self.business.id).exists())


class EmployeeInvitationTestCase(BaseAPITestCase):
    def setUp(self):
        # Create a business owner and a business
        self.owner_user = User.objects.create_user(
            email="owner@example.com",
            phone="912345601",
            password="ownerpass",
        )
        self.business = Business.objects.create(
            name="Invitation Business",
            address="123 Invite Road",
            category="Services",
            owner=self.owner_user,
        )
        # Create a creator employee (e.g. Admin)
        self.creator = User.objects.create_user(
            email="creator@example.com",
            phone="912345602",
            password="creatorpass",
        )
        self.creator_eb = EmployeeBusiness.objects.create(
            employee=self.creator,
            business=self.business,
            role=2,
            created_by=self.creator,
        )
        self.creator.save()
        self.creator_eb.save()

        invitation_create_url = reverse("employee-invite")
        invitation_param = {"business": self.business.id}
        self.invitation_create_url = (
            f"{invitation_create_url}?{urlencode(invitation_param)}"
        )
        # The accept URL pattern expects a token argument.
        # We'll build it dynamically in the acceptance test.

    def get_auth_headers(self, user):
        token = self.get_jwt_token(user)
        headers = {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
        }
        return headers

    @patch("accounts.views.requests.request")
    def test_employee_invitation_create(self, mock_request):
        """
        Ensure that an invitation is created and an email is attempted to be sent.
        """
        # Simulate a successful email API call
        mock_request.return_value.status_code = 200

        data = {
            "email": "invitee@example.com",
            "phone": "912345610",
            "role": 4,
        }
        headers = self.get_auth_headers(self.creator)
        response = self.client.post(
            self.invitation_create_url, data, format="json", **headers
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that an invitation object was created
        invitation = EmployeeInvitation.objects.filter(
            email="invitee@example.com"
        ).first()
        self.assertIsNotNone(invitation)
        self.assertFalse(invitation.accepted)

        # Assert that the email sending API was called
        self.assertTrue(mock_request.called)
        args, kwargs = mock_request.call_args
        # Check that the payload contains the acceptance link with the invitation token.
        payload = json.loads(kwargs.get("data", "{}"))
        self.assertIn(str(invitation.token), payload.get("message", ""))

    @patch("accounts.views.requests.request")
    def test_employee_invitation_accept(self, mock_request):
        """
        Ensure that hitting the accept URL immediately creates the employee using a temporary password,
        marks the invitation as accepted and attempts to send a congratulatory email.
        """
        # Simulate a successful email API call
        mock_request.return_value.status_code = 200

        # Create an invitation manually
        invitation = EmployeeInvitation.objects.create(
            email="invitee2@example.com",
            phone="912345611",
            role=4,
            created_by=self.creator,
            business=self.business,
        )

        accept_url = reverse("employee-invite-accept", args=[invitation.token])
        headers = self.get_auth_headers(self.creator)

        response = self.client.post(accept_url, **headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check that the employee was created with temporary password "password"
        employee = User.objects.filter(email="invitee2@example.com").first()
        eb = EmployeeBusiness.objects.filter(employee=employee).first()
        self.assertIsNotNone(employee)
        self.assertEqual(employee.email, invitation.email)
        self.assertEqual(eb.role, invitation.role)

        # Invitation should be marked as accepted.
        invitation.refresh_from_db()
        self.assertTrue(invitation.accepted)

        # Assert that the congratulatory email API was called.
        self.assertTrue(mock_request.called)
        args, kwargs = mock_request.call_args
        payload = json.loads(kwargs.get("data", "{}"))
        self.assertIn("Welcome Aboard", payload.get("subject", ""))


class EmployeeCRUDPermissionTestCase(BaseAPITestCase):
    def setUp(self):
        # Create users for testing
        self.admin = User.objects.create_superuser(
            email="adminemp@example.com", phone="912345681", password="adminpass"
        )
        self.owner = User.objects.create_user(
            email="owneremp@example.com", phone="912345682", password="ownerpass"
        )
        self.regular = User.objects.create_user(
            email="regularemp@example.com", phone="912345683", password="regularpass"
        )

        # Create a business for employee assignments.
        self.business = Business.objects.create(
            name="Employee Business",
            address="100 Business Rd",
            category="Services",
            owner=self.owner,
        )

        # Create EmployeeBusiness records for each user.
        self.admin_eb = EmployeeBusiness.objects.create(
            employee=self.admin,
            business=self.business,
            role=2,  # Role for admin, adjust as needed
            created_by=self.admin,
        )
        self.owner_eb = EmployeeBusiness.objects.create(
            employee=self.owner,
            business=self.business,
            role=1,  # Role for owner, adjust as needed
            created_by=self.owner,
        )
        self.regular_eb = EmployeeBusiness.objects.create(
            employee=self.regular,
            business=self.business,
            role=4,  # Role for regular user, adjust as needed
            created_by=self.owner,
        )

        # Create two employee users without business and role fields
        self.employee_by_owner = User.objects.create_user(
            email="emp1@example.com",
            phone="912345684",
            password="emppass1",
            first_name="First",
            last_name="Employee",
        )

        self.employee_other = User.objects.create_user(
            email="emp2@example.com",
            phone="912345685",
            password="emppass2",
            first_name="Second",
            last_name="Employee",
        )

        # Create separate EmployeeBusiness instances for each employee
        # Assuming EmployeeBusiness is the new model linking employees with a business and a role.
        EmployeeBusiness.objects.create(
            employee=self.employee_by_owner,
            business=self.business,
            role=4,
            created_by=self.owner,
        )

        EmployeeBusiness.objects.create(
            employee=self.employee_other,
            business=self.business,
            role=4,
            created_by=self.admin,
        )

    def get_headers(self, user):
        token = self.get_jwt_token(user)
        headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        return headers

    # ----- Delete tests -----
    def test_admin_can_delete_employee(self):
        """Admins should be allowed to delete an employee's EmployeeBusiness record."""
        url = reverse("employee-detail", args=[self.employee_other.id])
        params = {"business": self.business.id}
        url = f"{url}?{urlencode(params)}"
        headers = self.get_headers(self.admin)
        data = {"business": self.business.id, "role": 4}
        response = self.client.delete(url, data, **headers)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Ensure the EmployeeBusiness record is deleted...
        self.assertFalse(
            EmployeeBusiness.objects.filter(
                employee=self.employee_other, business=self.business, role=4
            ).exists()
        )
        # ...but the Employee is still intact.
        self.assertTrue(User.objects.filter(id=self.employee_other.id).exists())

    def test_owner_can_delete_employee(self):
        """Owners should be allowed to delete an employee's EmployeeBusiness record within their business."""
        url = reverse("employee-detail", args=[self.employee_other.id])
        params = {"business": self.business.id}
        url = f"{url}?{urlencode(params)}"
        headers = self.get_headers(self.owner)
        data = {"business": self.business.id, "role": 4}
        response = self.client.delete(url, data, **headers)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            EmployeeBusiness.objects.filter(
                employee=self.employee_other, business=self.business, role=4
            ).exists()
        )
        self.assertTrue(User.objects.filter(id=self.employee_other.id).exists())

    def test_non_permitted_user_cannot_delete_employee(self):
        """A user without proper permission should not be allowed to delete an employee's EmployeeBusiness record."""
        url = reverse("employee-detail", args=[self.employee_by_owner.id])
        params = {"business": self.business.id}
        url = f"{url}?{urlencode(params)}"
        headers = self.get_headers(self.regular)
        data = {"business": self.business.id, "role": 4}
        response = self.client.delete(url, data, **headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # The EmployeeBusiness record should still exist.
        self.assertTrue(
            EmployeeBusiness.objects.filter(
                employee=self.employee_by_owner, business=self.business, role=4
            ).exists()
        )

import datetime

from accounts.models import Business
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Customer, GiftCard

User = get_user_model()


class CustomerAPITests(APITestCase):
    def setUp(self):
        # Create a user and a business for the customer
        self.user = User.objects.create_user(
            email="customeruser@example.com",
            phone_number="912345678",
            first_name="Customer",
            last_name="User",
            password="test1234",
        )
        self.business = Business.objects.create(
            name="Test Business",
            owner=self.user,
            business_type=1,
        )
        self.customer_data = {
            "email": "newcustomer@example.com",
            "phone_number": "712345678",
            "full_name": "New Customer",
            "business": self.business.id,
        }
        self.list_url = "/crm/customers/"

    def test_create_customer(self):
        response = self.client.post(
            self.list_url,
            self.customer_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Customer.objects.count(), 1)
        customer = Customer.objects.first()
        self.assertEqual(customer.email, self.customer_data["email"])

    def test_get_customer_list(self):
        Customer.objects.create(
            email="existing@example.com",
            phone_number="712345678",
            full_name="Existing Customer",
            business=self.business,
        )
        response = self.client.get(self.list_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_update_customer(self):
        customer = Customer.objects.create(
            email="update@example.com",
            phone_number="712345678",
            full_name="Update Customer",
            business=self.business,
        )
        detail_url = f"{self.list_url}{customer.id}/"
        update_data = {"full_name": "Updated Name"}
        response = self.client.patch(detail_url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        customer.refresh_from_db()
        self.assertEqual(customer.full_name, "Updated Name")

    def test_delete_customer(self):
        customer = Customer.objects.create(
            email="delete@example.com",
            phone_number="712345678",
            full_name="Delete Customer",
            business=self.business,
        )
        detail_url = f"{self.list_url}{customer.id}/"
        response = self.client.delete(detail_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Customer.objects.filter(id=customer.id).exists())


class GiftCardAPITests(APITestCase):
    def setUp(self):
        # Create a user and a business for the gift card
        self.user = User.objects.create_user(
            email="giftcarduser@example.com",
            phone_number="912345678",
            first_name="Gift",
            last_name="CardUser",
            password="test1234",
        )
        self.business = Business.objects.create(
            name="Gift Business",
            owner=self.user,
            business_type=1,
        )
        self.giftcard_data = {
            "business": self.business.id,
            "owner": self.user.id,
            "created_by": self.user.id,
            "redeemed": False,
            "expires_at": (
                timezone.now()
                + datetime.timedelta(
                    days=30,
                )
            ).isoformat(),
            "type": 1,  # Specific Item
        }
        self.list_url = "/crm/giftcards/"

    def test_create_giftcard(self):
        response = self.client.post(
            self.list_url,
            self.giftcard_data,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(GiftCard.objects.count(), 1)
        giftcard = GiftCard.objects.first()
        self.assertEqual(giftcard.type, self.giftcard_data["type"])

    def test_get_giftcard_list(self):
        GiftCard.objects.create(
            business=self.business,
            owner=self.user,
            created_by=self.user,
            redeemed=False,
            expires_at=timezone.now() + datetime.timedelta(days=30),
            type=2,  # Business Item
        )
        response = self.client.get(self.list_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) >= 1)

    def test_update_giftcard(self):
        giftcard = GiftCard.objects.create(
            business=self.business,
            owner=self.user,
            created_by=self.user,
            redeemed=False,
            expires_at=timezone.now() + datetime.timedelta(days=30),
            type=3,  # Platform Item
        )
        detail_url = f"{self.list_url}{giftcard.id}/"
        update_data = {"redeemed": True}
        response = self.client.patch(detail_url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        giftcard.refresh_from_db()
        self.assertTrue(giftcard.redeemed)

    def test_delete_giftcard(self):
        giftcard = GiftCard.objects.create(
            business=self.business,
            owner=self.user,
            created_by=self.user,
            redeemed=False,
            expires_at=timezone.now() + datetime.timedelta(days=30),
            type=1,
        )
        detail_url = f"{self.list_url}{giftcard.id}/"
        response = self.client.delete(detail_url, format="json")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(GiftCard.objects.filter(id=giftcard.id).exists())

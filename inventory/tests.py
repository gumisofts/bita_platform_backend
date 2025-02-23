from decimal import Decimal
from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import (
    Category,
    Manufacturer,
    Location,
    Store,
    Item,
    Supply,
    SupplyReservation,
)


class DummyUser:
    id = 1
    email = "test@example.com"
    first_name = "Test"
    last_name = "User"
    phone = "123456789"
    is_authenticated = True


class TestItemViewSet(APITestCase):
    def setUp(self):
        self.auth_patcher = patch(
            "inventory.authentication.RemoteJWTAuthentication.authenticate",
            return_value=(DummyUser(), "testtoken"),
        )
        self.auth_patcher.start()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer testtoken")

        self.category1 = Category.objects.create(name="Category 1")
        self.category2 = Category.objects.create(name="Category 2")
        self.manufacturer1 = Manufacturer.objects.create(name="Manufacturer 1")
        self.manufacturer2 = Manufacturer.objects.create(name="Manufacturer 2")
        # Create 15 Items with varying attributes
        for i in range(15):
            Item.objects.create(
                name=f"Test Item {i}",
                description="A test description",
                category=self.category1 if i % 2 == 0 else self.category2,
                manufacturer=self.manufacturer1 if i % 2 == 0 else self.manufacturer2,
                isvisible=(i % 3 == 0),
                is_returnable=(i % 4 == 0),
                notify_below=5,
            )

    def tearDown(self):
        self.auth_patcher.stop()

    def test_filter_by_category(self):
        url = "/inventory/items/?category_id={}".format(self.category1.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify every returned item has the specified category
        for item in response.data["results"]:
            self.assertEqual(item["category"], self.category1.id)

    def test_filter_by_manufacturer(self):
        url = "/inventory/items/?manufacturer_id={}".format(self.manufacturer2.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertEqual(item["manufacturer"], self.manufacturer2.id)

    def test_filter_by_visible(self):
        url = "/inventory/items/?visible=true"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertTrue(item["isvisible"])

    def test_filter_by_returnable(self):
        url = "/inventory/items/?returnable=true"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertTrue(item["is_returnable"])

    def test_search(self):
        # Create an item with a unique name and description
        unique_item = Item.objects.create(
            name="UniqueSearchItem",
            description="Unique description for search",
            category=self.category1,
            manufacturer=self.manufacturer1,
            isvisible=True,
            is_returnable=True,
            notify_below=5,
        )
        url = "/inventory/items/?search=UniqueSearchItem"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertTrue(any(item["id"] == unique_item.id for item in results))

    def test_pagination(self):
        # By default, PAGE_SIZE is 10 so the first page should have 10 items and total count should be 15.
        url = "/inventory/items/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 15)
        self.assertEqual(len(response.data["results"]), 10)
        # Fetch the next page using the URL in the 'next' field
        next_url = response.data["next"]
        response_page2 = self.client.get(next_url)
        self.assertEqual(response_page2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_page2.data["results"]), 5)


class TestSupplyReservation(APITestCase):
    def setUp(self):
        self.auth_patcher = patch(
            "inventory.authentication.RemoteJWTAuthentication.authenticate",
            return_value=(DummyUser(), "testtoken"),
        )
        self.auth_patcher.start()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer testtoken")

        # Create a location and a store
        self.location = Location.objects.create(
            lat=0,
            lng=0,
            region="Test Region",
            zone="Test Zone",
            woreda="Test Woreda",
            kebele="Test Kebele",
            city="Test City",
            sub_city="Test Subcity",
        )
        self.store = Store.objects.create(
            business_id=1,
            name="Test Store",
            location=self.location,
        )
        # Create a simple item (without category/manufacturer details)
        self.item = Item.objects.create(
            name="Test Item",
            description="Test Description",
            category=None,
            manufacturer=None,
            barcode="ABC123",
            is_returnable=True,
            notify_below=5,
            isvisible=True,
        )
        # Create a supply linked to the item
        self.supply = Supply.objects.create(
            item=self.item,
            quantity=100,
            sale_price=Decimal("100.00"),
            cost_price=Decimal("50.00"),
            unit="Piece (pc)",
            expiration_date=None,
            batch_number="batch001",
            man_date=None,
            store=self.store,
            supplier_id=1,
        )

    def tearDown(self):
        self.auth_patcher.stop()

    def test_create_supply_reservation(self):
        url = reverse("reservations-list")
        data = {"supply": self.supply.id, "quantity": 10}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["supply"], self.supply.id)
        self.assertEqual(response.data["quantity"], 10)
        self.assertEqual(response.data["status"], "active")

    def test_list_supply_reservations(self):
        # Create two reservations
        res1 = SupplyReservation.objects.create(supply=self.supply, quantity=5)
        res2 = SupplyReservation.objects.create(supply=self.supply, quantity=15)
        url = reverse("reservations-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Ensure that both reservations are returned
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)
        ids = [res["id"] for res in response.data["results"]]
        self.assertIn(res1.id, ids)
        self.assertIn(res2.id, ids)

    def test_update_supply_reservation(self):
        # Create a reservation then update its status
        reservation = SupplyReservation.objects.create(supply=self.supply, quantity=20)
        url = reverse("reservations-detail", args=[reservation.id])
        data = {"status": "cancelled"}
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "cancelled")

    def test_delete_supply_reservation(self):
        # Create a reservation then delete it
        reservation = SupplyReservation.objects.create(supply=self.supply, quantity=8)
        url = reverse("reservations-detail", args=[reservation.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(SupplyReservation.objects.filter(id=reservation.id).exists())

    def test_invalid_reservation_quantity(self):
        # Ensure that a reservation with quantity 0 is not allowed
        url = reverse("reservations-list")
        data = {"supply": self.supply.id, "quantity": 0}  # invalid quantity
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", response.data)

    def test_reservation_quantity_exceeds_supply(self):
        # Assume self.supply.quantity is 100, so reserving 150 should be rejected
        url = reverse("reservations-list")
        data = {"supply": self.supply.id, "quantity": 150}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("quantity", response.data)

    def test_filter_supply_reservations_by_status(self):
        # Create reservations with different statuses
        res_active = SupplyReservation.objects.create(
            supply=self.supply, quantity=10, status="active"
        )
        res_cancelled = SupplyReservation.objects.create(
            supply=self.supply, quantity=5, status="cancelled"
        )
        res_fulfilled = SupplyReservation.objects.create(
            supply=self.supply, quantity=7, status="fulfilled"
        )

        url = reverse("reservations-list")

        # Filter by "active" status
        response = self.client.get(url + "?status=active")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], res_active.id)

        # Filter by "cancelled" status
        response = self.client.get(url + "?status=cancelled")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], res_cancelled.id)

        # Filter by "fulfilled" status
        response = self.client.get(url + "?status=fulfilled")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], res_fulfilled.id)

        # Filter by an invalid status; expect no results
        response = self.client.get(url + "?status=nonexistent")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_create_fulfilled_reservation_reduces_supply_quantity(self):
        # Get the initial supply quantity
        initial_quantity = self.supply.quantity
        url = reverse("reservations-list")
        data = {"supply": self.supply.id, "quantity": 30, "status": "fulfilled"}
        response = self.client.post(url, data, format="json")
        self.supply.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Supply quantity should be reduced by 30 immediately upon creation
        self.assertEqual(self.supply.quantity, initial_quantity - 30)

    def test_fulfilled_reservation_update_reduces_supply_quantity(self):
        # Create a reservation with status "active"
        reservation = SupplyReservation.objects.create(supply=self.supply, quantity=20)
        initial_quantity = self.supply.quantity
        url = reverse("reservations-detail", args=[reservation.id])
        data = {"status": "fulfilled"}
        response = self.client.patch(url, data, format="json")
        self.supply.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Supply quantity should be reduced by 20 after updating status to fulfilled
        self.assertEqual(self.supply.quantity, initial_quantity - 20)

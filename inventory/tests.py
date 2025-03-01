from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Business, Category
from .models import Item


class TestItemViewSet(APITestCase):
    def setUp(self):
        self.category1 = Category.objects.create(name="Category 1")
        self.category2 = Category.objects.create(name="Category 2")
        self.business1 = Business.objects.create(
            name="Business 1",
            business_type=1,
        )
        self.business2 = Business.objects.create(
            name="Business 2",
            business_type=2,
        )
        # Create 15 Items with varying attributes
        for i in range(15):
            Item.objects.create(
                name=f"Test Item {i}",
                description="A test description",
                category=self.category1 if i % 2 == 0 else self.category2,
                business=self.business1 if i % 2 == 0 else self.business2,
                inventory_unit="unit",
                selling_quota=10,
                notify_below=5,
                is_returnable=(i % 4 == 0),
                make_online_available=(i % 3 == 0),
            )

    def test_filter_by_category(self):
        url = "/inventory/items/?category_id={}".format(self.category1.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify every returned item has the specified category
        for item in response.data["results"]:
            self.assertEqual(item["category"], self.category1.id)

    def test_filter_by_business(self):
        url = "/inventory/items/?business_id={}".format(self.business2.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertEqual(item["business"], self.business2.id)

    def test_filter_by_returnable(self):
        url = "/inventory/items/?returnable=true"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertTrue(item["is_returnable"])

    def test_filter_by_online(self):
        url = "/inventory/items/?online=true"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for item in response.data["results"]:
            self.assertTrue(item["make_online_available"])

    def test_search(self):
        # Create an item with a unique name and description
        unique_item = Item.objects.create(
            name="UniqueSearchItem",
            description="Unique description for search",
            category=self.category1,
            business=self.business1,
            inventory_unit="unit",
            selling_quota=10,
            notify_below=5,
            is_returnable=True,
            make_online_available=True,
        )
        url = "/inventory/items/?search=UniqueSearchItem"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["results"]
        self.assertTrue(any(item["id"] == unique_item.id for item in results))

    def test_pagination(self):
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

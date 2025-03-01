# from decimal import Decimal

# from django.urls import reverse
# from rest_framework import status
# from rest_framework.test import APITestCase

# from .models import *


# class TestItemViewSet(APITestCase):
#     def setUp(self):

#         self.category1 = Category.objects.create(name="Category 1")
#         self.category2 = Category.objects.create(name="Category 2")
#         self.manufacturer1 = Manufacturer.objects.create(name="Manufacturer 1")
#         self.manufacturer2 = Manufacturer.objects.create(name="Manufacturer 2")
#         # Create 15 Items with varying attributes
#         for i in range(15):
#             Item.objects.create(
#                 name=f"Test Item {i}",
#                 description="A test description",
#                 category=self.category1 if i % 2 == 0 else self.category2,
#                 manufacturer=self.manufacturer1 if i % 2 == 0 else self.manufacturer2,
#                 isvisible=(i % 3 == 0),
#                 is_returnable=(i % 4 == 0),
#                 notify_below=5,
#             )

#     def test_filter_by_category(self):
#         url = "/inventory/items/?category_id={}".format(self.category1.id)
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         # Verify every returned item has the specified category
#         for item in response.data["results"]:
#             self.assertEqual(item["category"], self.category1.id)

#     def test_filter_by_manufacturer(self):
#         url = "/inventory/items/?manufacturer_id={}".format(self.manufacturer2.id)
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         for item in response.data["results"]:
#             self.assertEqual(item["manufacturer"], self.manufacturer2.id)

#     def test_filter_by_visible(self):
#         url = "/inventory/items/?visible=true"
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         for item in response.data["results"]:
#             self.assertTrue(item["isvisible"])

#     def test_filter_by_returnable(self):
#         url = "/inventory/items/?returnable=true"
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         for item in response.data["results"]:
#             self.assertTrue(item["is_returnable"])

#     def test_search(self):
#         # Create an item with a unique name and description
#         unique_item = Item.objects.create(
#             name="UniqueSearchItem",
#             description="Unique description for search",
#             category=self.category1,
#             manufacturer=self.manufacturer1,
#             isvisible=True,
#             is_returnable=True,
#             notify_below=5,
#         )
#         url = "/inventory/items/?search=UniqueSearchItem"
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         results = response.data["results"]
#         self.assertTrue(any(item["id"] == unique_item.id for item in results))

#     def test_pagination(self):
#         # By default, PAGE_SIZE is 10 so the first page should have 10 items and total count should be 15.
#         url = "/inventory/items/"
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["count"], 15)
#         self.assertEqual(len(response.data["results"]), 10)
#         # Fetch the next page using the URL in the 'next' field
#         next_url = response.data["next"]
#         response_page2 = self.client.get(next_url)
#         self.assertEqual(response_page2.status_code, status.HTTP_200_OK)
#         self.assertEqual(len(response_page2.data["results"]), 5)

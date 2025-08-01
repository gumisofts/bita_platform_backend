from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from accounts.models import User
from business.models import Business, Category, Industry
from inventories.models import Item, ItemVariant, Property

User = get_user_model()


# class MarketplaceProductViewSetTest(APITestCase):
#     """Test cases for marketplace product endpoints"""

#     def setUp(self):
#         # Create test user and business
#         self.user = User.objects.create_user(
#             email="test@example.com", password="testpass123"
#         )
#         self.client = APIClient()

#         # Create industry and category
#         self.industry = Industry.objects.create(name="Electronics", is_active=True)
#         self.category = Category.objects.create(
#             name="Smartphones", industry=self.industry, is_active=True
#         )

#         # Create business
#         self.business = Business.objects.create(
#             name="Tech Store",
#             owner=self.user,
#             business_type="retail",
#             is_active=True,
#             is_verified=True,
#         )
#         self.business.categories.add(self.category)

#         # Create items and variants
#         self.item = Item.objects.create(
#             name="iPhone 14",
#             description="Latest iPhone model",
#             inventory_unit="pieces",
#             business=self.business,
#         )
#         self.item.categories.add(self.category)

#         self.variant1 = ItemVariant.objects.create(
#             item=self.item,
#             name="iPhone 14 - 128GB",
#             quantity=50,
#             selling_price=999.99,
#             sku="IP14-128",
#             batch_number="BATCH001",
#             is_visible_online=True,
#             receive_online_orders=True,
#             notify_below=10,
#         )

#         self.variant2 = ItemVariant.objects.create(
#             item=self.item,
#             name="iPhone 14 - 256GB",
#             quantity=0,  # Out of stock
#             selling_price=1199.99,
#             sku="IP14-256",
#             batch_number="BATCH002",
#             is_visible_online=True,
#             receive_online_orders=True,
#             notify_below=5,
#         )

#         # Create properties
#         Property.objects.create(name="Color", value="Black", item_variant=self.variant1)
#         Property.objects.create(
#             name="Storage", value="128GB", item_variant=self.variant1
#         )

#     def test_product_list(self):
#         """Test product listing"""
#         url = reverse("marketplace-products-list")
#         response = self.client.get(url)
#         print(response.data)  # Debugging output
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["count"], 2)

#     def test_product_list_in_stock_only(self):
#         """Test filtering products in stock only"""
#         url = reverse("marketplace-products-list")
#         response = self.client.get(url, {"in_stock_only": "true"})

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["count"], 1)
#         self.assertEqual(response.data["results"][0]["name"], "iPhone 14 - 128GB")

#     def test_product_list_category_filter(self):
#         """Test filtering by category"""
#         url = reverse("marketplace-products-list")
#         response = self.client.get(url, {"categories": [str(self.category.id)]})

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["count"], 2)

#     def test_product_list_price_filter(self):
#         """Test price range filtering"""
#         url = reverse("marketplace-products-list")
#         response = self.client.get(url, {"min_price": "1000", "max_price": "1500"})

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["count"], 1)
#         self.assertEqual(response.data["results"][0]["name"], "iPhone 14 - 256GB")

#     def test_product_list_property_filter(self):
#         """Test filtering by properties"""
#         url = reverse("marketplace-products-list")
#         response = self.client.get(url, {"properties": "Color:Black"})

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["count"], 1)
#         self.assertEqual(response.data["results"][0]["name"], "iPhone 14 - 128GB")

#     def test_product_detail(self):
#         """Test product detail view"""
#         url = reverse("marketplace-products-detail", kwargs={"pk": self.variant1.pk})
#         response = self.client.get(url)

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["name"], "iPhone 14 - 128GB")
#         self.assertIn("properties", response.data)
#         self.assertEqual(len(response.data["properties"]), 2)

#     def test_product_search(self):
#         """Test product search"""
#         url = reverse("marketplace-products-list")
#         response = self.client.get(url, {"search": "iPhone"})

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["count"], 2)

#     def test_featured_products(self):
#         """Test featured products endpoint"""
#         url = reverse("marketplace-products-featured")
#         response = self.client.get(url)

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertIsInstance(response.data, list)

#     def test_similar_products(self):
#         """Test similar products endpoint"""
#         url = reverse("marketplace-products-similar", kwargs={"pk": self.variant1.pk})
#         response = self.client.get(url)

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertIsInstance(response.data, list)

#     def test_advanced_search(self):
#         """Test advanced search endpoint"""
#         url = reverse("marketplace-products-advanced-search")
#         data = {
#             "query": "iPhone",
#             "min_price": 500,
#             "max_price": 1500,
#             "in_stock_only": True,
#             "categories": [str(self.category.id)],
#         }
#         response = self.client.post(url, data, format="json")

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertIn("results", response.data)


class MarketplaceCategoryViewSetTest(APITestCase):
    """Test cases for marketplace category endpoints"""

    def setUp(self):
        self.industry = Industry.objects.create(name="Electronics", is_active=True)
        self.category = Category.objects.create(
            name="Smartphones", industry=self.industry, is_active=True
        )
        self.client = APIClient()

    def test_category_list(self):
        """Test category listing"""
        url = reverse("marketplace-categories-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_category_tree(self):
        """Test category tree endpoint"""
        url = reverse("marketplace-categories-tree")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)


class MarketplaceStatsViewSetTest(APITestCase):
    """Test cases for marketplace stats endpoints"""

    def setUp(self):
        self.client = APIClient()

    def test_overview_stats(self):
        """Test marketplace overview statistics"""
        url = reverse("marketplace-stats-overview")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_keys = [
            "total_products",
            "total_businesses",
            "total_categories",
            "products_in_stock",
            "verified_businesses",
        ]
        for key in expected_keys:
            self.assertIn(key, response.data)

    def test_categories_stats(self):
        """Test category statistics"""
        url = reverse("marketplace-stats-categories-stats")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

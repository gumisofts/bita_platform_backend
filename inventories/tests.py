# tests/test_items.py

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from business.models import Branch, Business, Category
from inventories.models import Group, Item, ItemVariant, Pricing, SuppliedItem, Supply

User = get_user_model()


class ItemViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="password123"
        )
        self.client.force_authenticate(user=self.user)
        self.business = Business.objects.create(name="Test Business")
        self.group = Group.objects.create(
            name="Test Group", description="Test Desc", business=self.business
        )
        self.category = Category.objects.create(
            name="Test Category", business=self.business
        )

        self.item = Item.objects.create(
            name="Test Item",
            description="Test description",
            group=self.group,
            min_selling_quota=1,
            inventory_unit="pcs",
            business=self.business,
        )
        self.item.categories.add(self.category)

    def test_list_items(self):
        url = reverse("items-list")  # assuming router is registered
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_item(self):
        url = reverse("items-list")
        data = {
            "name": "New Item",
            "description": "Another item",
            "group": str(self.group.id),
            "min_selling_quota": 1,
            "inventory_unit": "box",
            "business": str(self.business.id),
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Item.objects.count(), 2)

    def test_filter_by_business_id(self):
        url = reverse("items-list")
        response = self.client.get(url, {"business_id": self.business.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_filter_with_no_match(self):
        url = reverse("items-list")
        response = self.client.get(url, {"business_id": uuid4()})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)


# tests/test_supply.py
class SupplyViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="supplyuser@example.com", password="password123"
        )
        self.client.force_authenticate(user=self.user)
        self.business = Business.objects.create(name="Supply Business")
        self.branch = Branch.objects.create(name="Main Branch", business=self.business)
        self.supply = Supply.objects.create(label="Supply Label", branch=self.branch)

    def test_list_supplies(self):
        url = reverse("supplies-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_supply(self):
        url = reverse("supplies-list")
        data = {
            "label": "New Supply",
            "branch": str(self.branch.id),
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Supply.objects.count(), 2)

    def test_filter_by_business_id(self):
        url = reverse("supplies-list")
        response = self.client.get(url, {"business_id": self.business.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)


class SuppliedItemViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="supplieditemuser@example.com", password="password123"
        )
        self.client.force_authenticate(user=self.user)
        self.business = Business.objects.create(name="Supply Item Business")
        self.branch = Branch.objects.create(name="Branch", business=self.business)
        self.supply = Supply.objects.create(label="Supply Label", branch=self.branch)
        self.item = Item.objects.create(
            name="Supplied Item",
            description="desc",
            inventory_unit="pcs",
            business=self.business,
        )

        self.supplied_item = SuppliedItem.objects.create(
            quantity=10,
            item=self.item,
            purchase_price=50,
            batch_number="BATCH001",
            product_number="PROD001",
            business=self.business,
            supply=self.supply,
        )

    def test_create_supplied_item(self):
        url = reverse("supplied-items-list")
        data = {
            "quantity": 5,
            "item": str(self.item.id),
            "purchase_price": 100,
            "batch_number": "BATCH002",
            "product_number": "PROD002",
            "business": str(self.business.id),
            "supply": str(self.supply.id),
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SuppliedItem.objects.count(), 2)

    # def test_list_supplied_items_filtered_by_supply(self):
    #     url = reverse("supplied-items-list")
    #     response = self.client.get(url, {"supply_id": self.supply.id})
    #     self.assertEqual(response.status_code, status.HTTP_200_OK)
    #     self.assertEqual(len(response.data['results']), 1)


# tests/test_pricing.py


class PricingViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="pricinguser@example.com", password="password123"
        )
        self.client.force_authenticate(user=self.user)
        self.business = Business.objects.create(name="Pricing Business")
        self.item = Item.objects.create(
            name="Item for Pricing",
            description="desc",
            inventory_unit="pcs",
            business=self.business,
        )
        self.variant = ItemVariant.objects.create(
            item=self.item,
            name="Variant A",
            quantity=10,
            selling_price=20,
            batch_number="B123",
            sku="SKU123",
            notify_below=5,
        )

        self.pricing = Pricing.objects.create(
            price=100,
            item_variant=self.variant,
            min_selling_quota=1,
        )

    def test_list_pricings(self):
        url = reverse("pricings-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_pricing(self):
        url = reverse("pricings-list")
        data = {
            "price": 200,
            "item_variant": str(self.variant.id),
            "min_selling_quota": 2,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Pricing.objects.count(), 2)

    def test_filter_pricings_by_item(self):
        url = reverse("pricings-list")
        response = self.client.get(url, {"item_id": self.item.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should be empty because filter is on ItemVariant not Item (based on your view)


# tests/test_group.py


class GroupViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="groupuser@example.com", password="password123"
        )
        self.client.force_authenticate(user=self.user)
        self.business = Business.objects.create(name="Group Business")

        self.group = Group.objects.create(
            name="Test Group", description="Group Desc", business=self.business
        )

    def test_list_groups(self):
        url = reverse("groups-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_group(self):
        url = reverse("groups-list")
        data = {
            "name": "New Group",
            "description": "New Group Desc",
            "business": str(self.business.id),
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Group.objects.count(), 2)


class ItemVariantViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="variantuser@example.com", password="password123"
        )
        self.client.force_authenticate(user=self.user)
        self.business = Business.objects.create(name="Variant Business")
        self.item = Item.objects.create(
            name="Variant Item",
            description="desc",
            inventory_unit="pcs",
            business=self.business,
        )

        self.variant = ItemVariant.objects.create(
            item=self.item,
            name="Variant 1",
            quantity=5,
            selling_price=100,
            batch_number="VARBATCH001",
            sku="VARSKU001",
            notify_below=1,
        )

    def test_list_variants(self):
        url = reverse("item-variants-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

    def test_create_variant(self):
        url = reverse("item-variants-list")
        data = {
            "item": str(self.item.id),
            "name": "New Variant",
            "quantity": 10,
            "selling_price": 200,
            "batch_number": "NEWBATCH",
            "sku": "NEWSKU",
            "notify_below": 2,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ItemVariant.objects.count(), 2)

    def test_filter_variants_by_item(self):
        url = reverse("item-variants-list")
        response = self.client.get(url, {"item_id": self.item.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)

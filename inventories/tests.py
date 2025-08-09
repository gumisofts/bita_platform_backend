# tests/test_items.py

from uuid import uuid4

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from business.models import Branch, Business, Category
from inventories.models import (
    Group,
    InventoryMovement,
    InventoryMovementItem,
    Item,
    ItemVariant,
    Pricing,
    SuppliedItem,
    Supply,
)

User = get_user_model()


class ItemViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com", password="password123"
        )
        self.client.force_authenticate(user=self.user)
        self.business = Business.objects.create(name="Test Business", owner=self.user)
        self.group = Group.objects.create(
            name="Test Group", description="Test Desc", business=self.business
        )
        self.category = Category.objects.create(name="Test Category")

        self.branch = Branch.objects.get(business=self.business)

        self.item = Item.objects.create(
            name="Test Item",
            description="Test description",
            group=self.group,
            min_selling_quota=1,
            inventory_unit="pcs",
            business=self.business,
            branch=self.branch,
        )
        self.item.categories.add(self.category)

    def test_list_items(self):
        url = reverse("items-list")  # assuming router is registered
        response = self.client.get(url + "?business_id=" + str(self.business.id))
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
            "branch": str(self.branch.id),
        }
        response = self.client.post(url + "?business_id=" + str(self.business.id), data)
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
        self.business = Business.objects.create(name="Supply Business", owner=self.user)
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
        self.business = Business.objects.create(
            name="Supply Item Business", owner=self.user
        )
        self.branch = Branch.objects.create(name="Branch", business=self.business)
        self.supply = Supply.objects.create(label="Supply Label", branch=self.branch)
        self.item = Item.objects.create(
            name="Supplied Item",
            description="desc",
            inventory_unit="pcs",
            business=self.business,
            branch=self.branch,
        )
        self.variant = ItemVariant.objects.create(
            item=self.item,
            name="Variant A",
            quantity=10,
            selling_price=20,
            sku="SKU123",
        )

        self.supplied_item = SuppliedItem.objects.create(
            quantity=10,
            item=self.item,
            purchase_price=50,
            batch_number="BATCH001",
            product_number="PROD001",
            business=self.business,
            selling_price=20,
            supply=self.supply,
            variant=self.variant,
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
            "selling_price": 20,
            "supply": str(self.supply.id),
            "variant": str(self.variant.id),
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
        self.business = Business.objects.create(
            name="Pricing Business", owner=self.user
        )
        self.branch = Branch.objects.create(name="Branch", business=self.business)
        self.item = Item.objects.create(
            name="Item for Pricing",
            description="desc",
            inventory_unit="pcs",
            business=self.business,
            branch=self.branch,
        )
        self.variant = ItemVariant.objects.create(
            item=self.item,
            name="Variant A",
            quantity=10,
            selling_price=20,
            sku="SKU123",
        )

        self.pricing = Pricing.objects.create(
            price=100,
            item_variant=self.variant,
            min_selling_quota=1,
        )

    def test_create_pricing(self):
        url = reverse("pricings-list")
        data = {
            "price": 200,
            "item_variant": str(self.variant.id),
            "min_selling_quota": 2,
            "branch": str(self.branch.id),
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Pricing.objects.count(), 2)


# tests/test_group.py


class GroupViewSetTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="groupuser@example.com", password="password123"
        )
        self.client.force_authenticate(user=self.user)
        self.business = Business.objects.create(name="Group Business", owner=self.user)

        self.group = Group.objects.create(
            name="Test Group", description="Group Desc", business=self.business
        )

    def test_list_groups(self):
        url = reverse("groups-list")
        response = self.client.get(url + "?business_id=" + str(self.business.id))
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
        self.business = Business.objects.create(
            name="Variant Business", owner=self.user
        )
        self.branch = Branch.objects.create(name="Branch", business=self.business)
        self.item = Item.objects.create(
            name="Variant Item",
            description="desc",
            inventory_unit="pcs",
            business=self.business,
            branch=self.branch,
        )

        self.variant = ItemVariant.objects.create(
            item=self.item,
            name="Variant 1",
            quantity=5,
            selling_price=100,
            sku="VARSKU001",
        )

    def test_list_variants(self):
        url = reverse("item-variants-list")
        response = self.client.get(url + "?business_id=" + str(self.business.id))
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
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ItemVariant.objects.count(), 2)

    def test_filter_variants_by_item(self):
        url = reverse("item-variants-list")
        response = self.client.get(url + "?business_id=" + str(self.business.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)


class InventoryMovementTest(APITestCase):
    """Test cases for Inventory Movement functionality"""

    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="password123",
            first_name="Test",
            last_name="User",
        )
        self.client.force_authenticate(user=self.user)

        # Create business and branches
        self.business = Business.objects.create(name="Test Business", owner=self.user)

        self.branch_a = Branch.objects.create(name="Branch A", business=self.business)

        self.branch_b = Branch.objects.create(name="Branch B", business=self.business)

        # Create supplies and items
        self.supply_a = Supply.objects.create(label="Supply A", branch=self.branch_a)

        self.item = Item.objects.create(
            name="Test Item",
            description="Test Description",
            inventory_unit="pcs",
            business=self.business,
            branch=self.branch_a,
        )
        self.variant = ItemVariant.objects.create(
            item=self.item,
            name="Variant A",
            quantity=10,
            selling_price=20,
            sku="SKU123",
        )
        self.supplied_item = SuppliedItem.objects.create(
            quantity=100,
            item=self.item,
            purchase_price=50,
            batch_number="BATCH001",
            product_number="PROD001",
            business=self.business,
            selling_price=20,
            supply=self.supply_a,
            variant=self.variant,
        )

    def test_create_inventory_movement(self):
        """Test creating a new inventory movement"""
        url = reverse("inventory-movements-list")
        data = {
            "from_branch": str(self.branch_a.id),
            "to_branch": str(self.branch_b.id),
            "notes": "Test movement",
            "items": [
                {
                    "supplied_item_id": str(self.supplied_item.id),
                    "quantity": 10,
                    "notes": "Test item movement",
                    "variant": str(self.variant.id),
                }
            ],
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify movement was created
        movement = InventoryMovement.objects.get(id=response.data["id"])
        self.assertEqual(movement.from_branch, self.branch_a)
        self.assertEqual(movement.to_branch, self.branch_b)
        self.assertEqual(movement.status, "pending")
        self.assertEqual(movement.requested_by, self.user)

        # Verify movement item was created
        self.assertEqual(movement.movement_items.count(), 1)
        movement_item = movement.movement_items.first()
        self.assertEqual(movement_item.quantity_requested, 10)

    def test_approve_movement(self):
        """Test approving a pending movement"""
        # Create a movement
        movement = InventoryMovement.objects.create(
            from_branch=self.branch_a,
            to_branch=self.branch_b,
            business=self.business,
            requested_by=self.user,
            status="pending",
        )

        url = reverse("inventory-movements-approve", kwargs={"pk": movement.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        movement.refresh_from_db()
        self.assertEqual(movement.status, "approved")
        self.assertEqual(movement.approved_by, self.user)
        self.assertIsNotNone(movement.approved_at)

    def test_ship_movement(self):
        """Test shipping an approved movement"""
        # Create an approved movement with items
        movement = InventoryMovement.objects.create(
            from_branch=self.branch_a,
            to_branch=self.branch_b,
            business=self.business,
            requested_by=self.user,
            status="approved",
        )

        movement_item = InventoryMovementItem.objects.create(
            movement=movement,
            supplied_item=self.supplied_item,
            quantity_requested=10,
            variant=self.variant,
        )

        original_quantity = self.supplied_item.quantity

        url = reverse("inventory-movements-ship", kwargs={"pk": movement.id})
        data = {
            "items": [{"movement_item_id": movement_item.id, "quantity_shipped": 10}]
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify movement status updated
        movement.refresh_from_db()
        self.assertEqual(movement.status, "shipped")
        self.assertEqual(movement.shipped_by, self.user)

        # Verify inventory reduced
        self.supplied_item.refresh_from_db()
        self.assertEqual(self.supplied_item.quantity, original_quantity - 10)

        # Verify movement item updated
        movement_item.refresh_from_db()
        self.assertEqual(movement_item.quantity_shipped, 10)

    def test_receive_movement(self):
        """Test receiving a shipped movement"""
        # Create a shipped movement
        movement = InventoryMovement.objects.create(
            from_branch=self.branch_a,
            to_branch=self.branch_b,
            business=self.business,
            requested_by=self.user,
            status="shipped",
        )

        movement_item = InventoryMovementItem.objects.create(
            movement=movement,
            supplied_item=self.supplied_item,
            quantity_requested=10,
            quantity_shipped=10,
            variant=self.variant,
        )

        url = reverse("inventory-movements-receive", kwargs={"pk": movement.id})
        data = {
            "items": [{"movement_item_id": movement_item.id, "quantity_received": 10}]
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify movement status updated
        movement.refresh_from_db()
        self.assertEqual(movement.status, "received")
        self.assertEqual(movement.received_by, self.user)

        # Verify destination supply created
        destination_supply = Supply.objects.filter(
            branch=self.branch_b, label=self.supply_a.label
        ).first()
        self.assertIsNotNone(destination_supply)

        # Verify new supplied item created in destination
        destination_supplied_items = SuppliedItem.objects.filter(
            supply=destination_supply, item=self.item
        )
        self.assertEqual(destination_supplied_items.count(), 1)

        destination_item = destination_supplied_items.first()
        self.assertEqual(destination_item.quantity, 10)

    def test_cancel_movement(self):
        """Test cancelling a movement"""
        movement = InventoryMovement.objects.create(
            from_branch=self.branch_a,
            to_branch=self.branch_b,
            business=self.business,
            requested_by=self.user,
            status="pending",
        )

        url = reverse("inventory-movements-cancel", kwargs={"pk": movement.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        movement.refresh_from_db()
        self.assertEqual(movement.status, "cancelled")

    def test_invalid_branch_movement(self):
        """Test that movement between same branch is not allowed"""
        url = reverse("inventory-movements-list")
        data = {
            "from_branch": str(self.branch_a.id),
            "to_branch": str(self.branch_a.id),  # Same branch
            "notes": "Invalid movement",
            "items": [{"supplied_item_id": str(self.supplied_item.id), "quantity": 10}],
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

import unittest

from notifications.deep_links import deep_link_for_notification


class DeepLinkForNotificationTests(unittest.TestCase):
    def test_order_completed_with_order_id(self):
        self.assertEqual(
            deep_link_for_notification("order_completed", {"order_id": "abc-123"}),
            "bita://app/orders/abc-123",
        )

    def test_order_completed_without_order_id(self):
        self.assertEqual(
            deep_link_for_notification("order_completed", {}),
            "bita://app/orders",
        )

    def test_inventory_events_with_item_id(self):
        for event in ("low_stock", "restocked", "price_change", "product_updated"):
            with self.subTest(event=event):
                self.assertEqual(
                    deep_link_for_notification(event, {"item_id": "item-1"}),
                    "bita://app/inventory/item-1",
                )

    def test_inventory_events_without_item_id(self):
        self.assertEqual(
            deep_link_for_notification("low_stock", {}),
            "bita://app/inventory",
        )

    def test_inventory_movement(self):
        self.assertEqual(
            deep_link_for_notification("inventory_movement", {}),
            "bita://app/inventory",
        )

    def test_general_and_unknown_fallback(self):
        self.assertEqual(
            deep_link_for_notification("general", {}),
            "bita://app/notifications",
        )
        self.assertEqual(
            deep_link_for_notification("unknown_future_type", {}),
            "bita://app/notifications",
        )

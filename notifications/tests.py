import unittest
from unittest import mock

from django.test import override_settings
from rest_framework.test import APITestCase

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


class TelegramUpdateDispatchTests(unittest.TestCase):
    """The shared dispatcher used by both the webhook and the dev poller."""

    @override_settings(FRONTEND_URL="https://app.test")
    def test_start_offers_web_app_button_over_https(self):
        from notifications.telegram_updates import handle_update

        with mock.patch(
            "notifications.telegram_updates._send_bot_message_sync"
        ) as send:
            handle_update(
                {
                    "update_id": 1,
                    "message": {
                        "chat": {"id": 42},
                        "from": {"first_name": "Sam"},
                        "text": "/start",
                    },
                }
            )
        args, kwargs = send.call_args
        self.assertEqual(args[0], 42)
        self.assertIn("Sam", args[1])
        self.assertIn("web_app", str(kwargs.get("reply_markup")))

    @override_settings(FRONTEND_URL="http://localhost:5173")
    def test_fallback_uses_plain_link_without_https(self):
        from notifications.telegram_updates import handle_update

        with mock.patch(
            "notifications.telegram_updates._send_bot_message_sync"
        ) as send:
            handle_update(
                {"update_id": 2, "message": {"chat": {"id": 42}, "text": "hi"}}
            )
        args, kwargs = send.call_args
        self.assertIsNone(kwargs.get("reply_markup"))
        self.assertIn("localhost:5173", args[1])

    def test_non_message_update_is_ignored(self):
        from notifications.telegram_updates import handle_update

        with mock.patch(
            "notifications.telegram_updates._send_bot_message_sync"
        ) as send:
            handle_update({"update_id": 3, "callback_query": {}})
        send.assert_not_called()


class TelegramWebhookViewTests(APITestCase):
    URL = "/notifications/telegram/webhook/"
    UPDATE = {"update_id": 9, "message": {"chat": {"id": 7}, "text": "/start"}}

    @override_settings(TELEGRAM_WEBHOOK_SECRET="s3cret")
    def test_rejects_missing_or_wrong_secret(self):
        with mock.patch("notifications.telegram_updates.handle_update") as h:
            res = self.client.post(self.URL, self.UPDATE, format="json")
        self.assertEqual(res.status_code, 403)
        h.assert_not_called()

    @override_settings(TELEGRAM_WEBHOOK_SECRET="s3cret")
    def test_accepts_correct_secret(self):
        with mock.patch("notifications.telegram_updates.handle_update") as h:
            res = self.client.post(
                self.URL,
                self.UPDATE,
                format="json",
                HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="s3cret",
            )
        self.assertEqual(res.status_code, 200)
        h.assert_called_once()

    @override_settings(TELEGRAM_WEBHOOK_SECRET="")
    def test_always_200_even_when_handler_raises(self):
        with mock.patch(
            "notifications.telegram_updates.handle_update",
            side_effect=ValueError("boom"),
        ):
            res = self.client.post(self.URL, self.UPDATE, format="json")
        self.assertEqual(res.status_code, 200)

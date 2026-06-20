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


class TelegramNotificationDeliveryTests(APITestCase):
    """Rendering + delivery of Notifications over the Telegram bot."""

    def _make_notification(self, **kwargs):
        from notifications.models import Notification

        defaults = dict(
            title="Low Stock Alert",
            message="Sugar is running low.",
            event_type="low_stock",
            notification_type="warning",
            data={"deep_link": "bita://app/inventory/abc-123"},
        )
        defaults.update(kwargs)
        return Notification.objects.create(**defaults)

    @override_settings(FRONTEND_URL="https://app.test")
    def test_format_includes_title_message_and_app_button(self):
        from notifications.telegram_delivery import format_notification

        text, markup = format_notification(self._make_notification())
        self.assertIn("Low Stock Alert", text)
        self.assertIn("Sugar is running low.", text)
        # Deep link maps to the Mini App route under FRONTEND_URL.
        url = markup["inline_keyboard"][0][0]["web_app"]["url"]
        self.assertEqual(url, "https://app.test/inventory/abc-123")

    @override_settings(FRONTEND_URL="http://localhost:5173")
    def test_no_button_without_https_frontend(self):
        from notifications.telegram_delivery import format_notification

        _, markup = format_notification(self._make_notification())
        self.assertIsNone(markup)

    @override_settings(FRONTEND_URL="https://app.test")
    def test_html_in_title_is_escaped(self):
        from notifications.telegram_delivery import format_notification

        text, _ = format_notification(self._make_notification(title="A <b>B</b> & C"))
        self.assertIn("A &lt;b&gt;B&lt;/b&gt; &amp; C", text)

    def test_task_only_messages_linked_users(self):
        from accounts.models import User
        from notifications.tasks import send_telegram_notification_task

        linked = User.objects.create(
            email="linked@example.com", phone_number="911111111", telegram_id=4242
        )
        User.objects.create(email="nolink@example.com", phone_number="922222222")
        notification = self._make_notification()

        with mock.patch(
            "notifications.telegram_bot._send_bot_message_sync",
            return_value={"ok": True},
        ) as send:
            send_telegram_notification_task(
                str(notification.id),
                [str(linked.id)]
                + list(User.objects.exclude(id=linked.id).values_list("id", flat=True)),
            )

        # Only the linked user's telegram_id is messaged.
        self.assertEqual(send.call_count, 1)
        self.assertEqual(send.call_args.args[0], 4242)


class SendBotMessageTaskTests(unittest.TestCase):
    """Retry behaviour of the credential-DM task."""

    def test_permanent_failure_is_not_retried(self):
        from notifications.tasks import send_bot_message_task

        permanent = {
            "ok": False,
            "transient": False,
            "error_code": 403,
            "description": "Forbidden: bot can't initiate conversation with a user",
        }
        with mock.patch(
            "notifications.telegram_bot._send_bot_message_sync", return_value=permanent
        ):
            with mock.patch.object(send_bot_message_task, "retry") as retry:
                send_bot_message_task.run(123, "hi")
        retry.assert_not_called()

    def test_transient_failure_triggers_retry(self):
        from notifications.tasks import send_bot_message_task

        transient = {
            "ok": False,
            "transient": True,
            "error_code": 429,
            "description": "Too Many Requests",
        }
        with mock.patch(
            "notifications.telegram_bot._send_bot_message_sync", return_value=transient
        ):
            with mock.patch.object(
                send_bot_message_task, "retry", side_effect=RuntimeError("retried")
            ) as retry:
                with self.assertRaises(RuntimeError):
                    send_bot_message_task.run(123, "hi")
        retry.assert_called_once()


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

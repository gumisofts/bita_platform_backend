"""
Bita app deep links (bita://app/...) for notification payloads.

Routes align with the mobile app: inventory, orders, notifications, etc.
"""

BITA_APP_BASE = "bita://app"


def deep_link_for_notification(event_type: str, data: dict | None) -> str:
    """
    Return the deep link string for FCM `data["deep_link"]` (and stored Notification.data).

    Callers may set `data["deep_link"]` explicitly to override this mapping.
    """
    data = data or {}
    item_id = data.get("item_id")
    order_id = data.get("order_id")

    if event_type == "order_completed":
        if order_id:
            return f"{BITA_APP_BASE}/orders/{order_id}"
        return f"{BITA_APP_BASE}/orders"

    if event_type in (
        "low_stock",
        "restocked",
        "price_change",
        "product_updated",
    ):
        if item_id:
            return f"{BITA_APP_BASE}/inventory/{item_id}"
        return f"{BITA_APP_BASE}/inventory"

    if event_type == "inventory_movement":
        return f"{BITA_APP_BASE}/inventory"

    if event_type == "general":
        return f"{BITA_APP_BASE}/notifications"

    return f"{BITA_APP_BASE}/notifications"

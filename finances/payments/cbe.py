from datetime import datetime, timezone
from decimal import Decimal

from django.conf import settings

from .base import BaseVerifier, TransactionData


class CBEVerifier(BaseVerifier):

    def __init__(self, *args, **kwargs):
        self.receiver_account = kwargs.pop("receiver_account", "")
        super().__init__()

    BASE_URL = "https://mb.cbe.com.et/api/v1/transactions/public/transaction-detail/{transaction_id}"

    HEADERS = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Origin": "https://mbreciept.cbe.com.et",
        "Referer": "https://mbreciept.cbe.com.et/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.0.0 Safari/537.36"
        ),
        "x-app-id": "d1292e42-7400-49de-a2d3-9731caa4c819",
        "x-app-version": "0a01980b-9859-1369-8198-59f403820000",
    }

    def _full_transaction_id(self, transaction_id: str) -> str:
        """Append the last 8 digits of CBE_ACCOUNT_NO if not already present."""
        account_suffix = self.receiver_account[-8:]
        if f"-{account_suffix}" in transaction_id:
            return transaction_id
        return f"{transaction_id}-{account_suffix}".upper()

    RECEIPT_URL = "https://apps.cbe.com.et:100/?id={transaction_id}"

    def get_url(self, transaction_id: str, *args, **kwargs) -> str:
        return self.BASE_URL.format(
            transaction_id=self._full_transaction_id(transaction_id)
        )

    def get_receipt_url(self, transaction_id: str, receiver_account: str) -> str:
        return self.RECEIPT_URL.format(
            transaction_id=self._full_transaction_id(transaction_id)
        )

    def get_data(self, transaction_id: str, *args, **kwargs) -> TransactionData:
        raw = self.get_json(transaction_id)

        timestamp = None
        if raw.get("dateTimes"):
            timestamp = datetime.fromisoformat(
                raw["dateTimes"][0].replace("Z", "+00:00")
            ).astimezone(timezone.utc)

        return TransactionData(
            transaction_id=transaction_id,
            amount=Decimal(raw["amountCredited"]),
            sender_name=raw.get("debitAccountHolder"),
            receiver_name=raw.get("creditAccountHolder"),
            receiver_account=raw.get("creditAccountNo"),
            timestamp=timestamp,
            extra=raw,
        )

    # ── ownership checks ───────────────────────────────────────────────────
    # The CBE API masks the middle digits of the credited account, e.g.
    # ``1********6385`` for the real account ``1000331456385``. We compare
    # position-by-position, treating ``*`` as a wildcard, and additionally
    # confirm the receiver name against ``CBE_RECEIVER_NAME`` so a
    # malicious user can't reuse a receipt where only the suffix collides
    # with ours.

    def account_matches(self, masked: str | None, real: str | None) -> bool:
        if not masked or not real or len(masked) != len(real):
            return False
        return all(m == "*" or m == r for m, r in zip(masked, real))

    def does_the_account_match(self, data, expected_account):
        return self.account_matches(data.receiver_account, expected_account)

    def does_the_name_match(self, provided: str | None, expected: str | None) -> bool:
        if not expected:
            # Not configured → fall back to account-only verification.
            return True
        if not provided:
            return False
        return provided.strip().casefold() == expected.strip().casefold()

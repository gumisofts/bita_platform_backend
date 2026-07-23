import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

import requests
from bs4 import BeautifulSoup

# Ethiopian names are conventionally given as "First Father Grandfather...".
# Many people only enter their first and father's name (the part they consider
# their "full name" day-to-day), even though the name on their bank account
# includes further ancestors. We therefore only require the first two name
# parts to match, and simply compare however many parts are actually present
# on the shorter side.
NAME_PARTS_TO_MATCH = 2


def names_match(provided: str | None, expected: str | None) -> bool:
    """Return True if *provided* and *expected* agree on first + father name.

    Only the leading ``NAME_PARTS_TO_MATCH`` words of each name are compared
    (falling back to fewer words if a name is shorter), so extra trailing
    name parts (e.g. grandfather's name) present on either side are ignored.
    """
    if not expected:
        # Not configured → fall back to account-only verification.
        return True
    if not provided:
        return False

    def _leading_parts(name: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", name.strip()).casefold()
        return normalized.split(" ")[:NAME_PARTS_TO_MATCH]

    provided_parts = _leading_parts(provided)
    expected_parts = _leading_parts(expected)
    if not provided_parts or not expected_parts:
        return False

    compare_len = min(len(provided_parts), len(expected_parts))
    return provided_parts[:compare_len] == expected_parts[:compare_len]


@dataclass
class TransactionData:
    transaction_id: str
    amount: Decimal | None = None
    sender_name: str | None = None
    receiver_name: str | None = None
    receiver_account: str | None = None
    timestamp: datetime | None = None
    extra: dict = field(default_factory=dict)


class BaseVerifier(ABC):

    TIMEOUT = 10  # seconds
    HEADERS: dict = {}

    # ── helpers subclasses can call ──────────────────────────────────────────

    def _extra_request_kwargs(self) -> dict:
        """Subclass hook for ``proxies``, ``verify``, etc."""
        return {}

    def get_json(self, transaction_id: str) -> dict:
        response = requests.get(
            self.get_url(transaction_id),
            headers=self.HEADERS,
            timeout=self.TIMEOUT,
            **self._extra_request_kwargs(),
        )
        response.raise_for_status()
        return response.json()

    def get_html(self, transaction_id: str) -> str:
        response = requests.get(
            self.get_url(transaction_id),
            headers=self.HEADERS,
            timeout=self.TIMEOUT,
            **self._extra_request_kwargs(),
        )
        response.raise_for_status()
        return response.text

    def get_soup(self, transaction_id: str) -> BeautifulSoup:
        return BeautifulSoup(self.get_html(transaction_id), "html.parser")

    # ── abstract interface ───────────────────────────────────────────────────

    @abstractmethod
    def get_url(self, transaction_id: str, *args, **kwargs) -> str:
        """Return the URL for the transaction (receipt page or API endpoint)."""

    def get_receipt_url(self, transaction_id: str) -> str:
        """Public, human-viewable receipt URL.

        Used by the admin so reviewers can open the original receipt page
        in a browser. Defaults to ``get_url`` for providers whose ``get_url``
        already points at a viewable receipt page (e.g. Telebirr); override
        for providers where ``get_url`` is an API endpoint (e.g. CBE).
        """
        return self.get_url(transaction_id)

    @abstractmethod
    def get_data(self, transaction_id: str, *args, **kwargs) -> TransactionData:
        """Fetch and return parsed transaction data."""

    # ── concrete verify ──────────────────────────────────────────────────────

    def does_the_name_match(self, provided: str | None, expected: str | None) -> bool:
        """Return True if the receiver name matches the expected name.

        Only the first name and father's name (leading two words) need to
        match, since people commonly omit their grandfather's name (and
        beyond) even though it appears on their bank account.
        """
        return names_match(provided, expected)

    def does_the_account_match(
        self, data: TransactionData, expected_account: str
    ) -> bool:
        """Return True if the receiver account matches the expected account."""
        if not expected_account:
            # Not configured → fall back to name-only verification.
            return True
        if not data.receiver_account:
            return False
        return data.receiver_account.strip() == expected_account.strip()

    def does_the_amount_match(
        self, data: TransactionData, expected_amount: Decimal
    ) -> bool:
        """Return True if the amount matches the expected amount."""
        if expected_amount is None:
            # Not configured → skip amount verification.
            return True
        if data.amount is None:
            return False
        return data.amount == expected_amount

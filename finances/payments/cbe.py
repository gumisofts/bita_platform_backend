import re
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO

import requests
from dateutil import parser as dateutil_parser

from .base import BaseVerifier, TransactionData


class CBEVerifier(BaseVerifier):

    def __init__(self, *args, **kwargs):
        self.receiver_account = kwargs.pop("receiver_account", "")
        super().__init__()

    RECEIPT_BASE_URL = "https://apps.cbe.com.et:100/?id={transaction_id}"

    HEADERS = {
        "Accept": "application/pdf,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/147.0.0.0 Safari/537.36"
        ),
    }

    def _full_transaction_id(self, transaction_id: str) -> str:
        """Append the last 8 digits of the receiver account to the transaction ID.

        CBE receipt URLs use the format {base_id}{account_last_8}, e.g.
        FT26115CJJ8J + 31456385 → FT26115CJJ8J31456385.
        """
        if not self.receiver_account:
            return transaction_id.upper()
        account_suffix = self.receiver_account[-8:]
        upper_id = transaction_id.upper()
        # Legacy dash-separated form → normalise to no-dash (check before plain
        # suffix because both forms end with the same 8 digits).
        if upper_id.endswith(f"-{account_suffix}"):
            return upper_id[: -(len(account_suffix) + 1)] + account_suffix
        # Already in the correct no-dash form
        if upper_id.endswith(account_suffix):
            return upper_id
        return f"{upper_id}{account_suffix}"

    def get_url(self, transaction_id: str, *args, **kwargs) -> str:
        return self.RECEIPT_BASE_URL.format(
            transaction_id=self._full_transaction_id(transaction_id)
        )

    def get_receipt_url(self, transaction_id: str, receiver_account: str = "") -> str:
        return self.get_url(transaction_id)

    # ── PDF fetching & parsing ────────────────────────────────────────────

    def _get_pdf_text(self, transaction_id: str) -> str:
        """Fetch the receipt PDF and return all extracted text."""
        from pypdf import PdfReader

        url = self.get_url(transaction_id)
        response = requests.get(
            url,
            headers=self.HEADERS,
            timeout=self.TIMEOUT,
            **self._extra_request_kwargs(),
        )
        response.raise_for_status()
        reader = PdfReader(BytesIO(response.content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    def _parse_inline_field(self, text: str, label: str) -> str | None:
        """Return the value that appears on the same line after *label*."""
        pattern = re.compile(
            rf"^{re.escape(label)}\s+(.+?)\s*$",
            re.MULTILINE | re.IGNORECASE,
        )
        match = pattern.search(text)
        return match.group(1).strip() if match else None

    def get_data(self, transaction_id: str, *args, **kwargs) -> TransactionData:
        text = self._get_pdf_text(transaction_id)

        # ── Transferred Amount (amount received by the payee, before fees) ──
        amount = None
        amount_match = re.search(
            r"Transferred Amount\s+([\d,]+(?:\.\d+)?)\s+ETB",
            text,
            re.IGNORECASE,
        )
        if amount_match:
            amount = Decimal(amount_match.group(1).replace(",", ""))

        # ── Sender / payer ────────────────────────────────────────────────
        sender_name = self._parse_inline_field(text, "Payer")

        # ── Receiver name ─────────────────────────────────────────────────
        receiver_name = self._parse_inline_field(text, "Receiver")

        # ── Account numbers ───────────────────────────────────────────────
        # The receipt has two "Account <masked_no>" lines:
        # the first is the payer account, the second is the receiver account.
        account_lines = re.findall(
            r"^Account\s+(\S+)\s*$", text, re.MULTILINE | re.IGNORECASE
        )
        receiver_account = (
            account_lines[1]
            if len(account_lines) >= 2
            else (account_lines[0] if account_lines else None)
        )

        # ── Timestamp ─────────────────────────────────────────────────────
        timestamp = None
        ts_match = re.search(
            r"Payment Date & Time\s+(.+?)\s*$", text, re.MULTILINE | re.IGNORECASE
        )
        if ts_match:
            try:
                timestamp = dateutil_parser.parse(ts_match.group(1)).replace(
                    tzinfo=timezone.utc
                )
            except Exception:
                pass

        # ── Canonical transaction ID from the receipt ─────────────────────
        ref_match = re.search(
            r"Reference No\.\s*\(VAT Invoice No\)\s+(\S+)", text, re.IGNORECASE
        )
        canonical_id = ref_match.group(1) if ref_match else transaction_id

        return TransactionData(
            transaction_id=canonical_id,
            amount=amount,
            sender_name=sender_name,
            receiver_name=receiver_name,
            receiver_account=receiver_account,
            timestamp=timestamp,
            extra={"raw_text": text},
        )

    # ── ownership checks ──────────────────────────────────────────────────
    # CBE masks account numbers with a fixed 4-asterisk placeholder that does
    # NOT preserve the original length, e.g. ``1****6385`` for an account
    # whose full number is ``1000331456385``.  We therefore match by comparing
    # the visible prefix and suffix on either side of the asterisk block.

    def account_matches(self, masked: str | None, real: str | None) -> bool:
        if not masked or not real:
            return False
        # Length-preserving masking (legacy / other formats): compare char-by-char.
        if len(masked) == len(real):
            return all(m == "*" or m == r for m, r in zip(masked, real))
        # Non-length-preserving masking: visible_prefix + asterisks + visible_suffix.
        m = re.match(r"^([^*]+)\*+([^*]+)$", masked)
        if m:
            prefix, suffix = m.group(1), m.group(2)
            return real.startswith(prefix) and real.endswith(suffix)
        # Fully masked or unknown format — accept if masked appears inside real.
        return masked.replace("*", "") in real

    def does_the_account_match(
        self, data: TransactionData, expected_account: str
    ) -> bool:
        return self.account_matches(data.receiver_account, expected_account)

    def does_the_name_match(self, provided: str | None, expected: str | None) -> bool:
        if not expected:
            return True
        if not provided:
            return False
        return provided.strip().casefold() == expected.strip().casefold()

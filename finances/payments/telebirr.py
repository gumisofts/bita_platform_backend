from datetime import datetime
from decimal import Decimal

from bs4 import BeautifulSoup
from django.conf import settings

from .base import BaseVerifier, TransactionData, names_match

_TELEBIRR_RECEIPT_URL = (
    "https://transactioninfo.ethiotelecom.et/receipt/{transaction_id}"
)


class TelebirrVerifier(BaseVerifier):

    def __init__(self, *args, **kwargs):
        pass

    def _extra_request_kwargs(self) -> dict:
        """Use proxies if configured via TELEBIRR_PROXY_URL."""

        return {"verify": False}

    def get_url(self, transaction_id: str) -> str:
        base = (getattr(settings, "TELEBIRR_BASE_URL", "") or "").rstrip("/")
        if not base:
            base = "https://transactioninfo.ethiotelecom.et/receipt"
        return f"{base}/{transaction_id}"

    def get_receipt_url(self, transaction_id: str) -> str:
        return _TELEBIRR_RECEIPT_URL.format(transaction_id=transaction_id)

    def extract_from_html(self, transaction_id: str, html: str) -> TransactionData:
        soup = BeautifulSoup(html, "html.parser")
        data = TransactionData(transaction_id=transaction_id)

        def cell_after_label(label: str) -> str | None:
            """Find the smallest <td> whose text contains *label*.

            Returns the next sibling <td>'s text when the receipt is well-formed, or
            falls back to the first child <td> when the label cell is unclosed (a
            common malformation in Telebirr receipts where the value ends up nested).
            """
            for td in soup.find_all("td"):
                text = td.get_text()
                if label.lower() in text.lower() and len(text.strip()) < 200:
                    nxt = td.find_next_sibling("td")
                    if nxt:
                        return nxt.get_text(strip=True)
                    # Fallback: value is a child <td> (unclosed label cell)
                    child = td.find("td")
                    if child:
                        return child.get_text(strip=True)
            return None

        # ── payer / receiver ────────────────────────────────────────────────
        data.sender_name = cell_after_label("Payer Name")
        data.receiver_name = cell_after_label("Credited Party name")
        data.receiver_account = cell_after_label("Credited party account no")

        status = cell_after_label("transaction status")
        if status:
            data.extra["status"] = status

        # ── invoice details (Invoice No. | Payment date | Settled Amount) ──
        # The header row and the data row both use class receipttableTd2 on the
        # first cell. The header cell contains "Invoice No." – skip it and take
        # the next receipttableTd2 cell as the invoice number, then walk its
        # siblings for date and settled amount.
        td2_cells = soup.find_all("td", class_="receipttableTd2")
        for td in td2_cells:
            if "Invoice No." not in td.get_text():
                date_td = td.find_next_sibling("td")
                amount_td = date_td.find_next_sibling("td") if date_td else None
                if date_td:
                    date_str = date_td.get_text(strip=True)
                    try:
                        data.timestamp = datetime.strptime(
                            date_str, "%d-%m-%Y %H:%M:%S"
                        )
                    except ValueError:
                        pass
                if amount_td:
                    amount_str = (
                        amount_td.get_text(strip=True).replace("Birr", "").strip()
                    )
                    try:
                        data.amount = Decimal(amount_str)
                    except Exception:
                        pass
                break

        return data

    def get_data(self, transaction_id: str, *args, **kwargs) -> TransactionData:
        html = self.get_html(transaction_id)
        return self.extract_from_html(transaction_id, html)

    # ── ownership checks ───────────────────────────────────────────────────
    # Telebirr masks the middle of the credited-party number, e.g.
    # ``2519****2063``. Compare position-by-position (``*`` is wildcard)
    # after normalising both sides to international ``2519XXXXXXXX`` form,
    # and additionally confirm the receiver name against
    # ``TELEBIRR_RECEIVER_NAME``.

    @staticmethod
    def _normalize_msisdn(account: str | None) -> str | None:
        """Normalise an Ethiopian mobile number to ``2519XXXXXXXX`` form.

        Preserves ``*`` characters used by Telebirr's masking.
        """
        if not account:
            return account
        a = account.strip().replace("+", "").replace(" ", "").replace("-", "")
        if a.startswith("251"):
            return a
        if a.startswith("0"):
            return "251" + a[1:]
        if len(a) == 9:
            return "251" + a
        return a

    def account_matches(self, masked: str | None, real: str | None) -> bool:
        normalized = TelebirrVerifier._normalize_msisdn(masked)
        real = TelebirrVerifier._normalize_msisdn(real)
        if not normalized or not real or len(normalized) != len(real):
            return False
        return all(m == "*" or m == r for m, r in zip(normalized, real))

    def does_the_account_match(self, data, expected_account):
        return self.account_matches(data.receiver_account, expected_account)

    def does_the_name_match(self, provided: str | None, expected: str | None) -> bool:
        return names_match(provided, expected)

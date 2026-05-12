from dataclasses import asdict, dataclass, field
from datetime import datetime
from decimal import Decimal

from .base import BaseVerifier, TransactionData
from .cbe import CBEVerifier
from .telebirr import TelebirrVerifier


@dataclass
class VerificationResult:
    is_valid: bool
    validation_message: str
    extra: dict = field(default_factory=dict)
    data: TransactionData | None = None


class PaymentVerifier:
    """Utility class for verifying payment transactions across different providers."""

    def __init__(
        self,
        transaction_id: str,
        provider: str,
        account: str,
        expected_receiver_name: str | None = None,
        expected_amount: Decimal | None = None,
        *args,
        **kwargs,
    ):
        self.transaction_id = transaction_id
        self.provider = provider
        self.account = account
        self.expected_receiver_name = expected_receiver_name
        self.expected_amount = expected_amount

        self.args = args
        self.kwargs = kwargs

    def _get_verifier(self, provider_name: str) -> BaseVerifier | None:
        if provider_name.lower() == "cbe":
            return CBEVerifier(*self.args, **self.kwargs)
        elif provider_name.lower() == "telebirr":
            return TelebirrVerifier(*self.args, **self.kwargs)
        return None

    def verify_transaction(self) -> VerificationResult | None:
        verifier = self._get_verifier(self.provider)
        try:

            if not verifier:
                return VerificationResult(
                    is_valid=False,
                    validation_message=f"Unsupported provider: {self.provider}",
                    data=None,
                )

            data = verifier.get_data(self.transaction_id)

            if not verifier.does_the_account_match(
                data=data,
                expected_account=self.account,
            ):
                return VerificationResult(
                    is_valid=False,
                    validation_message="Transaction not credited to the expected account or receiver name.",
                    data=asdict(data),
                )

            if not verifier.does_the_name_match(
                provided=data.receiver_name,
                expected=self.expected_receiver_name,
            ):
                return VerificationResult(
                    is_valid=False,
                    validation_message="Receiver name does not match the expected name.",
                    data=asdict(data),
                )

            if not verifier.does_the_amount_match(
                data=data,
                expected_amount=self.expected_amount,
            ):
                return VerificationResult(
                    is_valid=False,
                    validation_message="Transaction amount does not match the expected amount.",
                    data=asdict(data),
                )

            return VerificationResult(
                is_valid=True,
                validation_message="Transaction verified successfully.",
                data=asdict(data),
            )

        except Exception as e:
            return VerificationResult(
                is_valid=False,
                validation_message=f"Error during verification: {str(e)}",
                data=None,
            )

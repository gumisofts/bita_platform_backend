from decimal import Decimal

from django.db.models import Count, Q, Sum
from rest_framework import serializers

from finances.models import BusinessPaymentMethod, PaymentMethod, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"
        depth = 1


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        exclude = []


class BusinessPaymentMethodSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = BusinessPaymentMethod
        exclude = []
        extra_kwargs = {
            "label": {"required": False, "allow_blank": True},
            "identifier": {"required": False, "allow_blank": True},
        }


class AccountSerializer(serializers.ModelSerializer):
    """Serializer that transforms BusinessPaymentMethod into account format."""

    name = serializers.CharField(source="display_name", read_only=True)
    type = serializers.SerializerMethodField()
    balance = serializers.SerializerMethodField()
    currency = serializers.CharField(default="ETB", read_only=True)
    account_number = serializers.SerializerMethodField()
    bank_name = serializers.SerializerMethodField()
    description = serializers.CharField(source="label", read_only=True)
    is_archived = serializers.BooleanField(default=False, read_only=True)
    is_deleted = serializers.BooleanField(default=False, read_only=True)

    class Meta:
        model = BusinessPaymentMethod
        fields = [
            "id",
            "name",
            "type",
            "balance",
            "currency",
            "created_at",
            "updated_at",
            "account_number",
            "bank_name",
            "description",
            "is_archived",
            "is_deleted",
        ]

    def get_type(self, obj):
        """Determine account type based on payment method name."""
        if not obj.payment:
            return 1  # Default to Cash

        payment_name_lower = obj.payment.name.lower()
        if "cash" in payment_name_lower:
            return 1  # Cash
        elif "credit" in payment_name_lower or "card" in payment_name_lower:
            return 2  # Credit Card
        else:
            return 0  # Bank

    def get_balance(self, obj):
        """Calculate balance from transactions."""
        transactions = Transaction.objects.filter(payment_method=obj)

        # Calculate balance: SALE and REFUND add, EXPENSE and DEBT subtract
        sale_refund_total = transactions.filter(
            type__in=[
                Transaction.TransactionType.SALE,
                Transaction.TransactionType.REFUND,
            ]
        ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")

        expense_debt_total = transactions.filter(
            type__in=[
                Transaction.TransactionType.EXPENSE,
                Transaction.TransactionType.DEBT,
            ]
        ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")

        balance = sale_refund_total - expense_debt_total
        return float(balance)

    def get_account_number(self, obj):
        """Return identifier as account number."""
        return obj.identifier if obj.identifier else None

    def get_bank_name(self, obj):
        """Extract bank name from payment method or return None."""
        if not obj.payment:
            return None

        payment_name = obj.payment.name
        # Try to extract bank name if it contains common bank keywords
        bank_keywords = ["bank", "ethiopia", "dashen", "commercial", "awash", "cbe"]
        for keyword in bank_keywords:
            if keyword.lower() in payment_name.lower():
                # Return capitalized version
                words = payment_name.split()
                if len(words) > 1:
                    return " ".join(word.capitalize() for word in words)
                return payment_name.capitalize()
        return None


class FinanceSummarySerializer(serializers.Serializer):
    """Serializer for finance summary endpoint."""

    total_assets = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_liabilities = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_worth = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_cash_flow = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_profit_margin = serializers.DecimalField(max_digits=5, decimal_places=2)
    previous_month_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    previous_month_expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    previous_month_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    year_to_date_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    year_to_date_expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    year_to_date_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_receivables = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_payables = serializers.DecimalField(max_digits=12, decimal_places=2)
    monthly_transactions = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    last_updated = serializers.DateTimeField()

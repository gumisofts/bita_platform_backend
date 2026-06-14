from decimal import Decimal

from django.db.models import Count, Q, Sum
from rest_framework import serializers

from finances.models import BusinessPaymentMethod, PaymentMethod, Transaction

from .payments import PaymentVerifier


class TransactionSerializer(serializers.ModelSerializer):
    is_settled = serializers.SerializerMethodField()
    customer_name = serializers.SerializerMethodField()

    def get_is_settled(self, obj) -> bool:
        """True when this credit transaction has been settled via the settle endpoint
        or via the legacy supply settle_debt flow."""
        if not obj.category:
            return False
        return obj.category.endswith(":settled") or obj.category.endswith(":paid")

    def get_customer_name(self, obj):
        """Return the linked order's customer full_name, if available."""
        try:
            if obj.order_id and obj.order and obj.order.customer_id:
                return obj.order.customer.full_name
        except Exception:
            pass
        return None

    class Meta:
        model = Transaction
        fields = "__all__"
        depth = 1


class TransactionCreateSerializer(serializers.ModelSerializer):
    """Write serializer for creating transactions directly via the API."""

    class Meta:
        model = Transaction
        fields = [
            "id",
            "order",
            "branch",
            "business",
            "payment_method",
            "created_by",
            "type",
            "total_paid_amount",
        ]
        read_only_fields = ["id", "created_by"]
        extra_kwargs = {
            "order": {"required": False, "allow_null": True},
            "payment_method": {"required": False, "allow_null": True},
            "category": {"required": False, "allow_blank": True, "allow_null": True},
        }

    def validate(self, attrs):
        branch = attrs.get("branch")
        business = attrs.get("business")
        if branch and business and branch.business_id != business.id:
            raise serializers.ValidationError(
                {"branch": "Branch does not belong to the specified business."}
            )
        return attrs


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
        """Calculate balance: all income types + REFUND add; all expense types + DEBT subtract."""
        transactions = Transaction.objects.filter(payment_method=obj)

        income_refund_total = transactions.filter(
            type__in=[
                *Transaction.INCOME_TYPES,
                Transaction.TransactionType.REFUND,
            ]
        ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")

        expense_debt_total = transactions.filter(
            type__in=[
                *Transaction.EXPENSE_TYPES,
                Transaction.TransactionType.DEBT,
            ]
        ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")

        return float(income_refund_total - expense_debt_total)

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


class HistoricalMonthSerializer(serializers.Serializer):
    month = serializers.DateTimeField()
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=12, decimal_places=2)


class ReportsSerializer(serializers.Serializer):
    date = serializers.DateTimeField()
    monthly_income = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2)
    )
    monthly_expense = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2)
    )
    total_monthly_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_monthly_expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=8, decimal_places=2)
    historical_data = HistoricalMonthSerializer(many=True)
    top_income_categories = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2)
    )
    top_expense_categories = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2)
    )


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


class PaymentMethodBreakdownSerializer(serializers.Serializer):
    payment_method_id = serializers.UUIDField()
    payment_method_name = serializers.CharField()
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_refunds = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    transaction_count = serializers.IntegerField()
    is_credit = serializers.BooleanField()
    pending_receivables = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_payables = serializers.DecimalField(max_digits=12, decimal_places=2)


class DailyBreakdownSerializer(serializers.Serializer):
    date = serializers.DateField()
    income = serializers.DecimalField(max_digits=12, decimal_places=2)
    expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    net = serializers.DecimalField(max_digits=12, decimal_places=2)
    transaction_count = serializers.IntegerField()


class PeriodComparisonSerializer(serializers.Serializer):
    previous_start = serializers.DateTimeField()
    previous_end = serializers.DateTimeField()
    previous_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    previous_expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    previous_net_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    income_change = serializers.DecimalField(max_digits=12, decimal_places=2)
    expense_change = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit_change = serializers.DecimalField(max_digits=12, decimal_places=2)
    income_change_pct = serializers.DecimalField(max_digits=8, decimal_places=2)
    expense_change_pct = serializers.DecimalField(max_digits=8, decimal_places=2)
    profit_change_pct = serializers.DecimalField(max_digits=8, decimal_places=2)


class FinanceReportSerializer(serializers.Serializer):
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()

    # Core income / expense metrics
    total_income = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_expense = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_refunds = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_debt_issued = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_profit = serializers.DecimalField(max_digits=12, decimal_places=2)
    profit_margin = serializers.DecimalField(max_digits=8, decimal_places=2)

    # Transaction-level metrics
    transaction_count = serializers.IntegerField()
    avg_transaction_value = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_receivables = serializers.DecimalField(max_digits=12, decimal_places=2)
    pending_payables = serializers.DecimalField(max_digits=12, decimal_places=2)

    # Breakdowns
    by_transaction_type = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2)
    )
    by_payment_method = PaymentMethodBreakdownSerializer(many=True)
    income_by_category = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2)
    )
    expense_by_category = serializers.DictField(
        child=serializers.DecimalField(max_digits=12, decimal_places=2)
    )

    # Order metrics
    total_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()

    # Trend data for charts
    daily_breakdown = DailyBreakdownSerializer(many=True)

    # Comparison against the previous equivalent period
    period_comparison = PeriodComparisonSerializer()


class PaymentVerificationSerializer(serializers.Serializer):
    transaction_id = serializers.CharField(write_only=True)

    business_payment_method = serializers.PrimaryKeyRelatedField(
        queryset=BusinessPaymentMethod.objects.all(), write_only=True
    )
    receiver_name = serializers.CharField(
        required=False, allow_blank=True, write_only=True
    )
    expected_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, write_only=True
    )

    message = serializers.CharField(read_only=True)
    is_valid = serializers.BooleanField(read_only=True)
    validation_message = serializers.CharField(read_only=True, allow_blank=True)
    data = serializers.JSONField(read_only=True, allow_null=True)

    def create(self, validated_data):

        business_payment_method = validated_data["business_payment_method"]
        payment_method = validated_data["business_payment_method"].payment
        account_number = validated_data["business_payment_method"].identifier
        receiver_name = (
            validated_data.get("receiver_name")
            or business_payment_method.receiver_name
            or business_payment_method.label
        )
        expected_amount = validated_data.get("expected_amount")

        return PaymentVerifier(
            transaction_id=validated_data["transaction_id"],
            provider=payment_method.short_name if payment_method else "",
            account=account_number if account_number else "",
            expected_receiver_name=receiver_name,
            expected_amount=expected_amount,
            receiver_account=business_payment_method.identifier,
        ).verify_transaction()

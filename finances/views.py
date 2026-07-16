from collections import defaultdict
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import Avg, Count, F, Q, Sum
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from business.models import Branch, Business, Employee, biz_perm
from business.permissions import (
    BranchLevelPermission,
    accessible_branches,
    filter_queryset_by_branch,
)
from core.idempotency import idempotent
from core.utils import is_valid_uuid
from finances.filters import BusinessPaymentMethodFilter, TransactionFilter
from inventories.models import Item, SuppliedItem
from orders.models import Order, OrderItem

from .models import BusinessPaymentMethod, PaymentMethod, Transaction
from .serializers import (
    AccountSerializer,
    BusinessPaymentMethodSerializer,
    FinanceReportSerializer,
    FinanceSummarySerializer,
    PaymentMethodSerializer,
    PaymentVerificationSerializer,
    ReportsSerializer,
    TransactionCreateSerializer,
    TransactionSerializer,
)


class TransactionViewset(
    CreateModelMixin, ListModelMixin, RetrieveModelMixin, GenericViewSet
):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    http_method_names = ["get", "post"]
    permission_classes = [IsAuthenticated, BranchLevelPermission]
    filterset_class = TransactionFilter

    def get_serializer_class(self):
        if self.action == "create":
            return TransactionCreateSerializer
        return TransactionSerializer

    def get_queryset(self):
        return (
            filter_queryset_by_branch(self.queryset, self.request, "transaction")
            .select_related(
                "order__customer",
                "branch",
                "business",
                "payment_method",
                "created_by",
            )
            .order_by("-created_at")
        )

    @idempotent
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        branch = serializer.validated_data.get("branch")
        business = serializer.validated_data.get("business")
        # Infer business from branch when not supplied explicitly.
        if branch and not business:
            business = branch.business

        # Fall back to request-level context set by middleware.
        if not branch and hasattr(self.request, "branch") and self.request.branch:
            branch = self.request.branch
        if not business and hasattr(self.request, "business") and self.request.business:
            business = self.request.business
        if branch and not business:
            business = branch.business

        serializer.save(branch=branch, business=business, created_by=self.request.user)

    @action(detail=True, methods=["post"], url_path="settle")
    @idempotent
    def settle(self, request, pk=None):
        """
        POST /finances/transactions/{id}/settle/

        Settle a credit transaction (receivable or payable) by recording
        the actual cash/bank payment.

        Body:
          - payment_method (UUID, required): real BPM to debit/credit
          - amount         (decimal, optional): partial amount; defaults to full amount
        """
        transaction = self.get_object()

        # Only credit transactions can be settled.
        if (
            not transaction.payment_method
            or transaction.payment_method.identifier != "CREDIT"
        ):
            raise ValidationError(
                {
                    "detail": "Only transactions on a CREDIT payment method can be settled."
                }
            )

        # Prevent double-settlement.
        if transaction.category and (
            transaction.category.endswith(":settled")
            or transaction.category.endswith(":paid")
        ):
            raise ValidationError(
                {"detail": "This transaction has already been settled."}
            )

        payment_method_id = request.data.get("payment_method")
        amount_raw = request.data.get("amount")

        if not payment_method_id:
            raise ValidationError({"payment_method": "This field is required."})

        try:
            payment_method = BusinessPaymentMethod.objects.get(id=payment_method_id)
        except BusinessPaymentMethod.DoesNotExist:
            raise ValidationError({"payment_method": "Payment method not found."})

        if payment_method.identifier == "CREDIT":
            raise ValidationError(
                {
                    "payment_method": "Cannot settle a credit transaction with another credit account."
                }
            )

        # Determine settlement amount.
        try:
            settle_amount = (
                Decimal(str(amount_raw)).quantize(Decimal("0.01"))
                if amount_raw
                else transaction.total_paid_amount
            )
        except Exception:
            raise ValidationError({"amount": "Enter a valid decimal amount."})

        if settle_amount <= 0:
            raise ValidationError({"amount": "Amount must be greater than zero."})
        if settle_amount > transaction.total_paid_amount:
            raise ValidationError(
                {
                    "amount": "Settlement amount cannot exceed the original transaction amount."
                }
            )

        # Determine the settlement transaction type:
        # - Income originals (SALE, SERVICE_REVENUE, OTHER_INCOME) → SALE settlement
        # - Expense originals (DEBT, EXPENSE, PURCHASE, …) → PURCHASE settlement
        if transaction.type in Transaction.INCOME_TYPES:
            settle_type = Transaction.TransactionType.SALE
        else:
            settle_type = Transaction.TransactionType.PURCHASE

        # Mark original transaction as settled (append :settled to category).
        original_category = transaction.category or ""
        transaction.category = (
            f"{original_category}:settled" if original_category else "settled"
        )
        transaction.save(update_fields=["category"])

        # Create settlement transaction.
        settlement = Transaction.objects.create(
            type=settle_type,
            total_paid_amount=settle_amount,
            payment_method=payment_method,
            business=transaction.business,
            branch=transaction.branch,
            category=f"settled:{transaction.id}",
            created_by=request.user,
        )

        return Response(
            TransactionSerializer(settlement).data, status=status.HTTP_201_CREATED
        )


# CRUD for Business Payment Methods
class BusinessPaymentMethodViewset(ModelViewSet):
    queryset = BusinessPaymentMethod.objects.all()
    serializer_class = BusinessPaymentMethodSerializer
    permission_classes = [IsAuthenticated, BranchLevelPermission]
    filterset_class = BusinessPaymentMethodFilter

    def get_queryset(self):
        queryset = filter_queryset_by_branch(
            self.queryset, self.request, "businesspaymentmethod"
        ).select_related("payment", "business", "branch")
        return queryset.filter(business=self.request.business)


class PaymentMethodViewset(ListModelMixin, GenericViewSet):
    queryset = PaymentMethod.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentMethodSerializer


class AccountViewset(ListModelMixin, GenericViewSet):
    """Viewset that returns BusinessPaymentMethod as accounts."""

    queryset = BusinessPaymentMethod.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [IsAuthenticated, BranchLevelPermission]

    def get_queryset(self):
        queryset = filter_queryset_by_branch(
            self.queryset, self.request, "businesspaymentmethod"
        )
        # Annotate the balance with two conditional sums over the single
        # ``transactions`` relation instead of running two aggregation queries
        # per account row in the serializer (was an N+1 of 2*page_size queries).
        return (
            queryset.filter(business=self.request.business)
            .select_related("payment")
            .annotate(
                _income_refund_total=Coalesce(
                    Sum(
                        "transactions__total_paid_amount",
                        filter=Q(
                            transactions__type__in=[
                                *Transaction.INCOME_TYPES,
                                Transaction.TransactionType.REFUND,
                            ]
                        ),
                    ),
                    Decimal("0.00"),
                ),
                _expense_debt_total=Coalesce(
                    Sum(
                        "transactions__total_paid_amount",
                        filter=Q(
                            transactions__type__in=[
                                *Transaction.EXPENSE_TYPES,
                                Transaction.TransactionType.DEBT,
                            ]
                        ),
                    ),
                    Decimal("0.00"),
                ),
            )
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def summary(request):
    """
    GET /finances/summary/

    Returns financial summary including assets, liabilities, income, expenses,
    and various metrics for the current and previous periods.
    """
    # Get business and branch from query params or request context
    business_id = request.query_params.get("business") or request.query_params.get(
        "business_id"
    )
    branch_id = request.query_params.get("branch") or request.query_params.get(
        "branch_id"
    )

    business = None
    branch = None

    # Get business from query params or middleware
    if business_id:
        if not is_valid_uuid(business_id):
            raise ValidationError({"detail": "Invalid business ID format"})
        try:
            business = Business.objects.get(id=business_id)
        except Business.DoesNotExist:
            raise ValidationError({"detail": "Business not found"})
    elif hasattr(request, "business") and request.business:
        business = request.business

    # Get branch from query params or middleware
    if branch_id:
        if not is_valid_uuid(branch_id):
            raise ValidationError({"detail": "Invalid branch ID format"})
        try:
            branch = Branch.objects.get(id=branch_id)
            if business and branch.business != business:
                raise ValidationError(
                    {"detail": "Branch does not belong to the specified business"}
                )
            elif not business:
                business = branch.business
        except Branch.DoesNotExist:
            raise ValidationError({"detail": "Branch not found"})
    elif hasattr(request, "branch") and request.branch:
        branch = request.branch
        if business and branch.business != business:
            raise ValidationError(
                {"detail": "Branch does not belong to the specified business"}
            )
        elif not business:
            business = branch.business

    if not business:
        raise ValidationError(
            {
                "detail": "Business is required. Provide 'business' or 'business_id' query parameter"
            }
        )

    if not branch:
        return Response(
            {"detail": "Branch is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    own_tx_filter, own_order_filter, _ = _report_transaction_scope(
        request, business, branch
    )

    # Base queryset filters
    transaction_filter = Q(business=business, branch=branch) & own_tx_filter
    order_filter = Q(business=business, branch=branch) & own_order_filter

    # Get current date and calculate date ranges
    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_month_start = (current_month_start - timedelta(days=1)).replace(day=1)
    previous_month_end = current_month_start - timedelta(seconds=1)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    # Get all transactions for the business/branch
    transactions = Transaction.objects.filter(transaction_filter)

    # Calculate total assets (sum of all payment method balances)
    # Assets = SALE + REFUND - EXPENSE - DEBT across all payment methods
    payment_methods_filter = Q(business=business)
    if branch:
        payment_methods_filter &= Q(branch=branch)
    else:
        payment_methods_filter &= Q(branch__isnull=True)
    payment_methods = BusinessPaymentMethod.objects.filter(payment_methods_filter)

    total_assets = Decimal("0.00")
    for pm in payment_methods:
        pm_transactions = transactions.filter(payment_method=pm)
        income_refund_total = pm_transactions.filter(
            type__in=[
                *Transaction.INCOME_TYPES,
                Transaction.TransactionType.REFUND,
            ]
        ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
        expense_debt_total = pm_transactions.filter(
            type__in=[
                *Transaction.EXPENSE_TYPES,
                Transaction.TransactionType.DEBT,
            ]
        ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
        total_assets += income_refund_total - expense_debt_total

    # Pending receivables/payables: transactions recorded against the CREDIT
    # payment method that have not yet been settled.
    credit_pm_filter = Q(payment_method__identifier="CREDIT")
    not_settled_filter = ~Q(category__endswith=":settled") & ~Q(
        category__endswith=":paid"
    )

    pending_receivables = transactions.filter(
        credit_pm_filter, type__in=Transaction.INCOME_TYPES
    ).filter(not_settled_filter).aggregate(total=Sum("total_paid_amount"))[
        "total"
    ] or Decimal(
        "0.00"
    )

    pending_payables = transactions.filter(
        credit_pm_filter,
        type__in=[*Transaction.EXPENSE_TYPES, Transaction.TransactionType.DEBT],
    ).filter(not_settled_filter).aggregate(total=Sum("total_paid_amount"))[
        "total"
    ] or Decimal(
        "0.00"
    )

    total_liabilities = pending_payables

    # Net worth
    net_worth = total_assets - total_liabilities

    def _sales_and_refunds(qs):
        """Return (total_sales, net_sales) for a transaction queryset.

        total_sales is gross SALE revenue; net_sales deducts refunds
        (refunds are stored negative, so it's an addition).
        """
        sales = qs.filter(type=Transaction.TransactionType.SALE).aggregate(
            total=Sum("total_paid_amount")
        )["total"] or Decimal("0.00")
        refunds = qs.filter(type=Transaction.TransactionType.REFUND).aggregate(
            total=Sum("total_paid_amount")
        )["total"] or Decimal("0.00")
        return sales, sales + refunds

    # Current month calculations
    current_month_transactions = transactions.filter(
        created_at__gte=current_month_start
    )
    monthly_income = current_month_transactions.filter(
        type__in=Transaction.INCOME_TYPES
    ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
    monthly_expense = current_month_transactions.filter(
        type__in=Transaction.EXPENSE_TYPES
    ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
    monthly_cash_flow = monthly_income - monthly_expense
    monthly_profit = monthly_cash_flow  # Assuming profit = cash flow for now
    monthly_profit_margin = (
        (monthly_profit / monthly_income * 100).quantize(Decimal("0.01"))
        if monthly_income > 0
        else Decimal("0.00")
    )
    monthly_total_sales, monthly_net_sales = _sales_and_refunds(
        current_month_transactions
    )

    # Previous month calculations
    previous_month_transactions = transactions.filter(
        created_at__gte=previous_month_start, created_at__lte=previous_month_end
    )
    previous_month_income = previous_month_transactions.filter(
        type__in=Transaction.INCOME_TYPES
    ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
    previous_month_expense = previous_month_transactions.filter(
        type__in=Transaction.EXPENSE_TYPES
    ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
    previous_month_profit = previous_month_income - previous_month_expense
    previous_month_total_sales, previous_month_net_sales = _sales_and_refunds(
        previous_month_transactions
    )

    # Year to date calculations
    ytd_transactions = transactions.filter(created_at__gte=year_start)
    year_to_date_income = ytd_transactions.filter(
        type__in=Transaction.INCOME_TYPES
    ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
    year_to_date_expense = ytd_transactions.filter(
        type__in=Transaction.EXPENSE_TYPES
    ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
    year_to_date_profit = year_to_date_income - year_to_date_expense
    year_to_date_total_sales, year_to_date_net_sales = _sales_and_refunds(
        ytd_transactions
    )

    # Monthly transactions count
    monthly_transactions = current_month_transactions.count()

    # Orders counts
    orders = Order.objects.filter(order_filter)
    completed_orders = orders.filter(status=Order.StatusChoices.COMPLETED).count()
    pending_orders = orders.filter(status=Order.StatusChoices.PENDING).count()

    # In-store inventory value at selling price (current stock on hand).
    total_inventory_value = _get_inventory_value(business, branch)

    # Prepare summary data
    summary_data = {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": net_worth,
        "total_inventory_value": total_inventory_value,
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "monthly_cash_flow": monthly_cash_flow,
        "monthly_profit": monthly_profit,
        "monthly_profit_margin": monthly_profit_margin,
        "monthly_total_sales": monthly_total_sales,
        "monthly_net_sales": monthly_net_sales,
        "previous_month_income": previous_month_income,
        "previous_month_expense": previous_month_expense,
        "previous_month_profit": previous_month_profit,
        "previous_month_total_sales": previous_month_total_sales,
        "previous_month_net_sales": previous_month_net_sales,
        "year_to_date_income": year_to_date_income,
        "year_to_date_expense": year_to_date_expense,
        "year_to_date_profit": year_to_date_profit,
        "year_to_date_total_sales": year_to_date_total_sales,
        "year_to_date_net_sales": year_to_date_net_sales,
        "pending_receivables": pending_receivables,
        "pending_payables": pending_payables,
        "monthly_transactions": monthly_transactions,
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,
        "last_updated": now,
    }

    serializer = FinanceSummarySerializer(summary_data)
    return Response(serializer.data)


def _resolve_business_branch(request):
    """
    Parse and validate business/branch from query params or request middleware.
    Returns (business, branch) or raises ValidationError.
    """
    business_id = request.query_params.get("business") or request.query_params.get(
        "business_id"
    )
    branch_id = request.query_params.get("branch") or request.query_params.get(
        "branch_id"
    )

    business = None
    branch = None

    if business_id:
        if not is_valid_uuid(business_id):
            raise ValidationError({"detail": "Invalid business ID format"})
        try:
            business = Business.objects.get(id=business_id)
        except Business.DoesNotExist:
            raise ValidationError({"detail": "Business not found"})
    elif hasattr(request, "business") and request.business:
        business = request.business

    if branch_id:
        if not is_valid_uuid(branch_id):
            raise ValidationError({"detail": "Invalid branch ID format"})
        try:
            branch = Branch.objects.get(id=branch_id)
            if business and branch.business != business:
                raise ValidationError(
                    {"detail": "Branch does not belong to the specified business"}
                )
            elif not business:
                business = branch.business
        except Branch.DoesNotExist:
            raise ValidationError({"detail": "Branch not found"})
    elif hasattr(request, "branch") and request.branch:
        branch = request.branch
        if not business:
            business = branch.business

    if not business:
        raise ValidationError(
            {
                "detail": "Business is required. Provide 'business' or 'business_id' query parameter"
            }
        )

    return business, branch


def _report_transaction_scope(request, business, branch):
    """Return (tx_filter, order_filter) that scope data to the caller's access level.

    - Full permission holders (can_view_transaction_branch): no extra filter → sees everything.
    - Employees without that permission: sees only their own transactions (created_by)
      and their own orders (employee field).
    - No employee record found: empty querysets.

    Returns a 3-tuple:
      own_tx_filter        — applied to Transaction querysets
      own_order_filter     — applied to Order querysets   (direct employee field)
      own_order_item_filter— applied to OrderItem querysets (traverses order__employee)
    """
    if branch and request.user.has_perm(
        biz_perm("transaction", "view", "branch"), branch
    ):
        return Q(), Q(), Q()

    employee = Employee.objects.filter(user=request.user, business=business).first()
    if not employee:
        empty = Q(pk__in=[])
        return empty, empty, empty

    return (
        Q(created_by=request.user),
        Q(employee=employee),
        Q(order__employee=employee),
    )


def _get_inventory_value(business, branch):
    """
    Total in-store value of current stock, valued at each supplied item's
    selling price: sum(quantity * selling_price) across all active items'
    supplied-item batches (i.e. what the inventory on hand would be worth
    if sold in full at current selling prices).
    """
    items_qs = Item.objects.filter(business=business, is_active=True)
    if branch:
        items_qs = items_qs.filter(branch=branch)

    value = SuppliedItem.objects.filter(item__in=items_qs).aggregate(
        total=Sum(F("quantity") * F("selling_price"))
    )["total"]
    return value or Decimal("0.00")


def _get_income_by_category(order_filter):
    """
    Aggregate sales revenue by item category from OrderItems.
    Items with no category are grouped under 'Other'.
    """
    items = (
        OrderItem.objects.filter(order_filter)
        .select_related("variant__item")
        .prefetch_related("variant__item__categories")
    )

    income_by_category = defaultdict(Decimal)
    for item in items:
        categories = list(item.variant.item.categories.all())
        category_name = categories[0].name if categories else "Other"
        price = (
            item.price
            or (item.supplied_item.selling_price if item.supplied_item else None)
            or Decimal("0")
        )
        income_by_category[category_name] += item.quantity * price

    return dict(income_by_category)


def _get_income_by_item_category(transaction_filter):
    """
    Aggregate all income revenue by item category.

    - SALE transactions that have an associated order: revenue is derived from
      the order's items and grouped by each item's first category
      (e.g. "Cosmetics"). Items with no category fall into "Other".
    - All remaining income (SALE without an order, SERVICE_REVENUE,
      OTHER_INCOME, etc.) is summed from total_paid_amount and added to "Other".
    """
    income_by_category = defaultdict(Decimal)

    # --- 1. SALE transactions with order details → group by item category ---
    order_ids = (
        Transaction.objects.filter(
            transaction_filter,
            type=Transaction.TransactionType.SALE,
            order__isnull=False,
        )
        .values_list("order_id", flat=True)
        .distinct()
    )

    order_items = (
        OrderItem.objects.filter(order_id__in=order_ids)
        .select_related("variant__item")
        .prefetch_related("variant__item__categories")
    )

    for oi in order_items:
        try:
            categories = list(oi.variant.item.categories.all())
            category_name = categories[0].name if categories else "Other"
        except AttributeError:
            category_name = "Other"
        price = (
            oi.price
            or (oi.supplied_item.selling_price if oi.supplied_item else None)
            or Decimal("0")
        )
        income_by_category[category_name] += oi.quantity * price

    # --- 2. All other income transactions → "Other" bucket ---
    # Excludes SALE transactions that already have an order (counted above).
    other_total = Transaction.objects.filter(
        transaction_filter,
        type__in=Transaction.INCOME_TYPES,
    ).exclude(
        type=Transaction.TransactionType.SALE,
        order__isnull=False,
    ).aggregate(
        total=Sum("total_paid_amount")
    )[
        "total"
    ] or Decimal(
        "0.00"
    )

    if other_total:
        income_by_category["Other"] += other_total

    return dict(income_by_category)


def _get_expense_by_category(transaction_filter):
    """
    Aggregate expense transactions by their category field.
    All EXPENSE_TYPES are included; transactions with no category are grouped under 'Other'.
    """
    expense_transactions = Transaction.objects.filter(
        transaction_filter, type__in=Transaction.EXPENSE_TYPES
    ).values("category", "total_paid_amount")

    expense_by_category = defaultdict(Decimal)
    for tx in expense_transactions:
        category_name = tx["category"] or "Other"
        expense_by_category[category_name] += tx["total_paid_amount"]

    return dict(expense_by_category)


def _month_range(year, month):
    """Return (start, end) datetime for a given year/month (UTC-aware)."""
    import calendar

    start = datetime(year, month, 1, 0, 0, 0, tzinfo=dt_timezone.utc)
    last_day = calendar.monthrange(year, month)[1]
    end = datetime(year, month, last_day, 23, 59, 59, 999999, tzinfo=dt_timezone.utc)
    return start, end


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reports(request):
    """
    GET /finances/reports/

    Query params:
      - business / business_id (required)
      - branch / branch_id (optional)
      - date: YYYY-MM (month to report on, defaults to current month)
      - history_months: int (number of past months in historical_data, default 12)

    Returns income/expense breakdown by category, profit metrics, and
    historical monthly data for the requested date range.
    """
    business, branch = _resolve_business_branch(request)

    if not branch:
        raise ValidationError({"detail": "Branch is required."})

    own_tx_filter, _, own_order_item_filter = _report_transaction_scope(
        request, business, branch
    )

    # Parse report date (YYYY-MM format)
    date_param = request.query_params.get("date")
    now = timezone.now()
    if date_param:
        try:
            report_year, report_month = [int(p) for p in date_param.split("-")[:2]]
        except (ValueError, AttributeError):
            raise ValidationError(
                {"detail": "Invalid date format. Use YYYY-MM (e.g. 2026-03)"}
            )
    else:
        report_year, report_month = now.year, now.month

    # Parse history_months
    try:
        history_months = int(request.query_params.get("history_months", 12))
        if history_months < 1:
            history_months = 12
    except ValueError:
        history_months = 12

    # Date range for the requested month
    period_start, period_end = _month_range(report_year, report_month)

    # Base filters (already know branch is set from the guard above)
    base_tx_filter = Q(business=business, branch=branch) & own_tx_filter
    base_order_filter = (
        Q(
            order__business=business,
            order__branch=branch,
            order__status__in=[
                Order.StatusChoices.COMPLETED,
                Order.StatusChoices.PAID,
                Order.StatusChoices.PARTIALLY_PAID,
                Order.StatusChoices.DELIVERED,
            ],
        )
        & own_order_item_filter
    )

    # Monthly income by category (from order items)
    month_order_filter = base_order_filter & Q(
        order__created_at__gte=period_start, order__created_at__lte=period_end
    )
    monthly_income_by_category = _get_income_by_category(month_order_filter)

    # Monthly expense by category (from expense transactions)
    month_tx_filter = base_tx_filter & Q(
        created_at__gte=period_start, created_at__lte=period_end
    )
    monthly_expense_by_category = _get_expense_by_category(month_tx_filter)

    total_monthly_income = sum(monthly_income_by_category.values(), Decimal("0"))
    total_monthly_expense = sum(monthly_expense_by_category.values(), Decimal("0"))
    net_profit = total_monthly_income - total_monthly_expense
    profit_margin = (
        (net_profit / total_monthly_income * 100).quantize(Decimal("0.01"))
        if total_monthly_income > 0
        else Decimal("0.00")
    )

    # Historical data: last N months ending at the report month
    historical_data = []
    for i in range(history_months - 1, -1, -1):
        # Go back i months from the report month
        month = report_month - i
        year = report_year
        while month <= 0:
            month += 12
            year -= 1

        h_start, h_end = _month_range(year, month)

        h_order_filter = base_order_filter & Q(
            order__created_at__gte=h_start, order__created_at__lte=h_end
        )
        h_tx_filter = base_tx_filter & Q(created_at__gte=h_start, created_at__lte=h_end)

        h_income_by_cat = _get_income_by_category(h_order_filter)
        h_expense_by_cat = _get_expense_by_category(h_tx_filter)

        h_total_income = sum(h_income_by_cat.values(), Decimal("0"))
        h_total_expense = sum(h_expense_by_cat.values(), Decimal("0"))

        historical_data.append(
            {
                "month": h_start,
                "total_income": h_total_income,
                "total_expense": h_total_expense,
                "net_profit": h_total_income - h_total_expense,
            }
        )

    # Top income by item category: SALE transactions with order details, grouped by category
    top_income = dict(
        sorted(
            _get_income_by_item_category(month_tx_filter).items(),
            key=lambda x: x[1],
            reverse=True,
        )
    )
    top_expense = dict(
        sorted(monthly_expense_by_category.items(), key=lambda x: x[1], reverse=True)
    )

    report_data = {
        "date": period_start,
        "monthly_income": monthly_income_by_category,
        "monthly_expense": monthly_expense_by_category,
        "total_monthly_income": total_monthly_income,
        "total_monthly_expense": total_monthly_expense,
        "net_profit": net_profit,
        "profit_margin": profit_margin,
        "historical_data": historical_data,
        "top_income_categories": top_income,
        "top_expense_categories": top_expense,
    }

    serializer = ReportsSerializer(report_data)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def finance_report(request):
    """
    GET /finances/finance-report/

    Comprehensive financial report with flexible date-range and dimension filters.

    Query params:
      - business / business_id  (required)
      - branch / branch_id      (optional)
      - start_date              YYYY-MM-DD (required)
      - end_date                YYYY-MM-DD, not inclusive (required)
      - payment_method          Comma-separated BusinessPaymentMethod UUID(s) (optional)
      - transaction_type        Comma-separated: SALE,EXPENSE,DEBT,REFUND (optional)

    Response includes:
      - Core metrics: income, expense, refunds, debt, net profit, margin
      - Transaction counts and averages
      - Pending receivables / payables
      - Breakdowns by transaction type, payment method, category
      - Order summary
      - Daily trend data for charts
      - Comparison against the previous equivalent period
    """
    business, branch = _resolve_business_branch(request)

    if not branch:
        raise ValidationError({"detail": "Branch is required."})

    own_tx_filter, own_order_filter, own_order_item_filter = _report_transaction_scope(
        request, business, branch
    )

    # --- Parse date range -----------------------------------------------
    start_date_param = request.query_params.get("start_date")
    end_date_param = request.query_params.get("end_date")

    if not start_date_param or not end_date_param:
        raise ValidationError(
            {"detail": "Both start_date and end_date are required (YYYY-MM-DD)."}
        )

    tz_utc3 = dt_timezone(timedelta(hours=3))

    try:
        start_date = datetime.strptime(start_date_param, "%Y-%m-%d").replace(
            tzinfo=tz_utc3
        )
    except ValueError:
        raise ValidationError({"detail": "Invalid start_date format. Use YYYY-MM-DD."})

    try:
        end_date = datetime.strptime(end_date_param, "%Y-%m-%d").replace(tzinfo=tz_utc3)
    except ValueError:
        raise ValidationError({"detail": "Invalid end_date format. Use YYYY-MM-DD."})

    if end_date <= start_date:
        raise ValidationError({"detail": "end_date must be after start_date."})

    # --- Parse optional filters -----------------------------------------
    # payment_method: comma-separated BusinessPaymentMethod UUIDs
    payment_method_param = request.query_params.get("payment_method")
    payment_method_ids = None
    if payment_method_param:
        raw_ids = [
            pid.strip() for pid in payment_method_param.split(",") if pid.strip()
        ]
        valid_ids = [pid for pid in raw_ids if is_valid_uuid(pid)]
        if valid_ids:
            payment_method_ids = valid_ids

    # transaction_type: comma-separated SALE|EXPENSE|DEBT|REFUND
    transaction_type_param = request.query_params.get("transaction_type")
    transaction_types = None
    if transaction_type_param:
        valid_tx_types = {c[0] for c in Transaction.TransactionType.choices}
        transaction_types = [
            t.strip().upper()
            for t in transaction_type_param.split(",")
            if t.strip().upper() in valid_tx_types
        ] or None

    # --- Build base queryset filter -------------------------------------
    # end_date is NOT inclusive → use __lt
    base_filter = Q(business=business, branch=branch) & Q(
        created_at__gte=start_date, created_at__lt=end_date
    )
    if payment_method_ids:
        base_filter &= Q(payment_method__in=payment_method_ids)
    if transaction_types:
        base_filter &= Q(type__in=transaction_types)
    base_filter &= own_tx_filter

    transactions = Transaction.objects.filter(base_filter)

    # --- Core summary metrics -------------------------------------------
    type_totals = (
        Transaction.objects.filter(
            Q(business=business, branch=branch)
            & Q(created_at__gte=start_date, created_at__lt=end_date)
            & (Q(payment_method__in=payment_method_ids) if payment_method_ids else Q())
            & own_tx_filter
        )
        .values("type")
        .annotate(total=Sum("total_paid_amount"))
    )
    totals_by_type = {row["type"]: row["total"] or Decimal("0") for row in type_totals}

    total_income = sum(
        totals_by_type.get(t, Decimal("0")) for t in Transaction.INCOME_TYPES
    )
    total_expense = sum(
        totals_by_type.get(t, Decimal("0")) for t in Transaction.EXPENSE_TYPES
    )
    # Refunds are stored negative, so total_refunds is <= 0.
    total_refunds = totals_by_type.get(Transaction.TransactionType.REFUND, Decimal("0"))
    total_income += total_refunds
    total_debt_issued = totals_by_type.get(
        Transaction.TransactionType.DEBT, Decimal("0")
    )

    # Sales revenue specifically (as opposed to total_income, which also
    # includes service revenue / other income). total_sales is the gross
    # figure before refunds are deducted; net_sales nets them out.
    total_sales = totals_by_type.get(Transaction.TransactionType.SALE, Decimal("0"))
    net_sales = total_sales + total_refunds

    # Refunds reduce profit. They are not in EXPENSE_TYPES (so not in
    # total_expense); fold them in via their negative sign instead.
    net_profit = total_income - total_expense
    profit_margin = (
        (net_profit / total_income * 100).quantize(Decimal("0.01"))
        if total_income > 0
        else Decimal("0.00")
    )

    # In-store inventory value at selling price — a point-in-time figure
    # (current stock on hand), not scoped to the report's date range.
    total_inventory_value = _get_inventory_value(business, branch)

    transaction_count = transactions.count()
    total_amount = transactions.aggregate(total=Sum("total_paid_amount"))[
        "total"
    ] or Decimal("0")
    avg_transaction_value = (
        (total_amount / transaction_count).quantize(Decimal("0.01"))
        if transaction_count > 0
        else Decimal("0.00")
    )

    credit_pm_filter = Q(payment_method__identifier="CREDIT")
    not_settled_filter = ~Q(category__endswith=":settled") & ~Q(
        category__endswith=":paid"
    )

    pending_receivables = transactions.filter(
        credit_pm_filter, type__in=Transaction.INCOME_TYPES
    ).filter(not_settled_filter).aggregate(total=Sum("total_paid_amount"))[
        "total"
    ] or Decimal(
        "0"
    )

    pending_payables = transactions.filter(
        credit_pm_filter,
        type__in=[*Transaction.EXPENSE_TYPES, Transaction.TransactionType.DEBT],
    ).filter(not_settled_filter).aggregate(total=Sum("total_paid_amount"))[
        "total"
    ] or Decimal(
        "0"
    )

    # --- By transaction type breakdown ----------------------------------
    by_transaction_type = {
        t: totals_by_type.get(t, Decimal("0"))
        for t in Transaction.TransactionType.values
    }

    # --- By payment method breakdown ------------------------------------
    pm_filter = Q(business=business, branch=branch) | Q(
        business=business, branch__isnull=True
    )
    if payment_method_ids:
        pm_filter &= Q(id__in=payment_method_ids)

    payment_methods = BusinessPaymentMethod.objects.filter(pm_filter).select_related(
        "payment"
    )

    # Refund totals must always reflect real REFUND transactions, independent
    # of the optional `transaction_type` filter. That filter narrows which
    # rows count as income/expense in `transactions` above (e.g.
    # transaction_type=SALE,EXPENSE); without this separate, unfiltered-by-type
    # queryset, any such filter would silently zero out total_refunds per
    # payment method even when refunds exist for the period (this mirrors how
    # the top-level total_refunds is already computed, unaffected by that
    # filter).
    refund_scope_filter = Q(business=business, branch=branch) & Q(
        created_at__gte=start_date, created_at__lt=end_date
    )
    if payment_method_ids:
        refund_scope_filter &= Q(payment_method__in=payment_method_ids)
    refund_scope_filter &= own_tx_filter
    refund_transactions = Transaction.objects.filter(
        refund_scope_filter, type=Transaction.TransactionType.REFUND
    )

    by_payment_method = []
    for pm in payment_methods:
        pm_txs = transactions.filter(payment_method=pm)
        pm_income = pm_txs.filter(type__in=Transaction.INCOME_TYPES).aggregate(
            total=Sum("total_paid_amount")
        )["total"] or Decimal("0")
        pm_expense = pm_txs.filter(type__in=Transaction.EXPENSE_TYPES).aggregate(
            total=Sum("total_paid_amount")
        )["total"] or Decimal("0")
        pm_refunds = refund_transactions.filter(payment_method=pm).aggregate(
            total=Sum("total_paid_amount")
        )["total"] or Decimal("0")

        pm_income += pm_refunds  # Refunds are negative, so add them to income
        is_credit_pm = pm.identifier == "CREDIT"
        pm_pending_receivables = pm_income if is_credit_pm else Decimal("0")
        pm_pending_payables = pm_expense if is_credit_pm else Decimal("0")
        by_payment_method.append(
            {
                "payment_method_id": pm.id,
                "payment_method_name": pm.display_name,
                "total_income": pm_income,
                "total_expense": pm_expense,
                "total_refunds": pm_refunds,
                "net_balance": pm_income - pm_expense,
                "transaction_count": pm_txs.count(),
                "is_credit": is_credit_pm,
                "pending_receivables": pm_pending_receivables,
                "pending_payables": pm_pending_payables,
            }
        )

    # Transactions with no payment method (e.g. orders completed without one)
    # are grouped under an "Unknown" entry. Skipped when filtering to specific
    # payment methods, since "unknown" can't match a requested id.
    if not payment_method_ids:
        unknown_txs = transactions.filter(payment_method__isnull=True)
        unknown_refunds = refund_transactions.filter(
            payment_method__isnull=True
        ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0")
        unknown_count = unknown_txs.count()
        # Include this bucket if there are matching (possibly type-filtered)
        # transactions OR real refunds, so refunds never get silently
        # dropped when transaction_type filters out every other row.
        if unknown_count or unknown_refunds:
            unknown_income = unknown_txs.filter(
                type__in=Transaction.INCOME_TYPES
            ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0")
            unknown_expense = unknown_txs.filter(
                type__in=Transaction.EXPENSE_TYPES
            ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0")
            unknown_income += (
                unknown_refunds  # Refunds are negative, so add them to income
            )
            by_payment_method.append(
                {
                    "payment_method_id": None,
                    "payment_method_name": "Unknown",
                    "total_income": unknown_income,
                    "total_expense": unknown_expense,
                    "total_refunds": unknown_refunds,
                    "net_balance": unknown_income - unknown_expense,
                    "transaction_count": unknown_count,
                    "is_credit": False,
                    "pending_receivables": Decimal("0"),
                    "pending_payables": Decimal("0"),
                }
            )

    # --- Income by category (from completed order items) ----------------
    order_filter = Q(
        order__business=business,
        order__branch=branch,
        order__status__in=[
            Order.StatusChoices.COMPLETED,
            Order.StatusChoices.PAID,
            Order.StatusChoices.PARTIALLY_PAID,
            Order.StatusChoices.DELIVERED,
        ],
        order__created_at__gte=start_date,
        order__created_at__lt=end_date,
    )
    if payment_method_ids:
        order_filter &= Q(order__payment_method__in=payment_method_ids)
    order_filter &= own_order_item_filter

    income_by_category = _get_income_by_category(order_filter)
    income_by_category = dict(
        sorted(income_by_category.items(), key=lambda x: x[1], reverse=True)
    )

    # --- Expense by category (from expense transactions) ----------------
    expense_cat_filter = Q(business=business, branch=branch) & Q(
        created_at__gte=start_date, created_at__lt=end_date
    )
    if payment_method_ids:
        expense_cat_filter &= Q(payment_method__in=payment_method_ids)
    expense_cat_filter &= own_tx_filter

    expense_by_category = _get_expense_by_category(expense_cat_filter)
    expense_by_category = dict(
        sorted(expense_by_category.items(), key=lambda x: x[1], reverse=True)
    )

    # --- Order summary --------------------------------------------------
    order_qs_filter = Q(business=business, branch=branch) & Q(
        created_at__gte=start_date, created_at__lt=end_date
    )
    if payment_method_ids:
        order_qs_filter &= Q(payment_method__in=payment_method_ids)
    order_qs_filter &= own_order_filter

    orders = Order.objects.filter(order_qs_filter)
    total_orders = orders.count()
    completed_orders = orders.filter(status=Order.StatusChoices.COMPLETED).count()
    pending_orders = orders.filter(status=Order.StatusChoices.PENDING).count()
    cancelled_orders = orders.filter(status=Order.StatusChoices.CANCELLED).count()

    # --- Daily breakdown ------------------------------------------------
    daily_qs = (
        transactions.annotate(day=TruncDate("created_at"))
        .values("day", "type")
        .annotate(total=Sum("total_paid_amount"), count=Count("id"))
        .order_by("day")
    )
    daily_map = defaultdict(
        lambda: {
            "income": Decimal("0"),
            "expense": Decimal("0"),
            "transaction_count": 0,
        }
    )
    for row in daily_qs:
        d = row["day"]
        tx_type = row["type"]
        amount = row["total"] or Decimal("0")
        if tx_type in Transaction.INCOME_TYPES:
            daily_map[d]["income"] += amount
        elif tx_type in Transaction.EXPENSE_TYPES:
            daily_map[d]["expense"] += amount
        daily_map[d]["transaction_count"] += row["count"]

    daily_breakdown = [
        {
            "date": d,
            "income": data["income"],
            "expense": data["expense"],
            "net": data["income"] - data["expense"],
            "transaction_count": data["transaction_count"],
        }
        for d, data in sorted(daily_map.items())
    ]

    # --- Period comparison (previous equivalent period) -----------------
    period_duration = end_date - start_date
    prev_end = start_date
    prev_start = start_date - period_duration

    prev_filter = Q(business=business, branch=branch) & Q(
        created_at__gte=prev_start, created_at__lt=prev_end
    )
    if payment_method_ids:
        prev_filter &= Q(payment_method__in=payment_method_ids)
    prev_filter &= own_tx_filter

    prev_type_totals = (
        Transaction.objects.filter(prev_filter)
        .values("type")
        .annotate(total=Sum("total_paid_amount"))
    )
    prev_totals_by_type = {
        row["type"]: row["total"] or Decimal("0") for row in prev_type_totals
    }
    previous_income = sum(
        prev_totals_by_type.get(t, Decimal("0")) for t in Transaction.INCOME_TYPES
    )
    previous_expense = sum(
        prev_totals_by_type.get(t, Decimal("0")) for t in Transaction.EXPENSE_TYPES
    )
    previous_refunds = prev_totals_by_type.get(
        Transaction.TransactionType.REFUND, Decimal("0")
    )
    previous_income += previous_refunds
    previous_net_profit = previous_income - previous_expense
    previous_total_sales = prev_totals_by_type.get(
        Transaction.TransactionType.SALE, Decimal("0")
    )
    previous_net_sales = previous_total_sales + previous_refunds

    def _pct_change(current, previous):
        if previous > 0:
            return ((current - previous) / previous * 100).quantize(Decimal("0.01"))
        return Decimal("0.00")

    period_comparison = {
        "previous_start": prev_start,
        "previous_end": prev_end,
        "previous_income": previous_income,
        "previous_expense": previous_expense,
        "previous_net_profit": previous_net_profit,
        "previous_total_sales": previous_total_sales,
        "previous_net_sales": previous_net_sales,
        "income_change": total_income - previous_income,
        "expense_change": total_expense - previous_expense,
        "profit_change": net_profit - previous_net_profit,
        "total_sales_change": total_sales - previous_total_sales,
        "net_sales_change": net_sales - previous_net_sales,
        "income_change_pct": _pct_change(total_income, previous_income),
        "expense_change_pct": _pct_change(total_expense, previous_expense),
        "profit_change_pct": _pct_change(net_profit, previous_net_profit),
        "total_sales_change_pct": _pct_change(total_sales, previous_total_sales),
        "net_sales_change_pct": _pct_change(net_sales, previous_net_sales),
    }

    report_data = {
        "start_date": start_date,
        "end_date": end_date,
        "total_income": total_income,
        "total_expense": total_expense,
        "total_refunds": total_refunds,
        "total_debt_issued": total_debt_issued,
        "total_sales": total_sales,
        "net_sales": net_sales,
        "total_inventory_value": total_inventory_value,
        "net_profit": net_profit,
        "profit_margin": profit_margin,
        "transaction_count": transaction_count,
        "avg_transaction_value": avg_transaction_value,
        "pending_receivables": pending_receivables,
        "pending_payables": pending_payables,
        "by_transaction_type": by_transaction_type,
        "by_payment_method": by_payment_method,
        "income_by_category": income_by_category,
        "expense_by_category": expense_by_category,
        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,
        "cancelled_orders": cancelled_orders,
        "daily_breakdown": daily_breakdown,
        "period_comparison": period_comparison,
    }

    serializer = FinanceReportSerializer(report_data)
    return Response(serializer.data)


class PaymentVerifyViewset(CreateModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentVerificationSerializer

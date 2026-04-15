from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from guardian.shortcuts import get_objects_for_user
from rest_framework import status, viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.mixins import ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from business.models import Branch, Business
from business.permissions import (
    AdditionalBusinessPermissionNames,
    BranchLevelPermission,
    BusinessLevelPermission,
    GuardianObjectPermissions,
)
from core.utils import is_valid_uuid
from inventories.models import SuppliedItem
from orders.models import Order, OrderItem

from .models import BusinessPaymentMethod, PaymentMethod, Transaction
from .serializers import (
    AccountSerializer,
    BusinessPaymentMethodSerializer,
    FinanceSummarySerializer,
    PaymentMethodSerializer,
    ReportsSerializer,
    TransactionSerializer,
)


class TransactionViewset(ListModelMixin, GenericViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    http_method_names = ["get", "post"]
    permission_classes = [
        IsAuthenticated,
        BusinessLevelPermission | BranchLevelPermission | GuardianObjectPermissions,
    ]

    def get_queryset(self):
        queryset = self.queryset
        user = self.request.user

        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_TRANSACTION.value[0]
            + "_business",
            self.request.business,
        ):
            queryset = queryset.filter(business=self.request.business)
        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_TRANSACTION.value[0] + "_branch",
            self.request.branch,
        ):
            queryset = queryset.filter(branch=self.request.branch)
        else:
            queryset = queryset.none()
        return queryset


# CRUD for Business Payment Methods
class BusinessPaymentMethodViewset(ModelViewSet):
    queryset = BusinessPaymentMethod.objects.all()
    serializer_class = BusinessPaymentMethodSerializer
    permission_classes = [
        IsAuthenticated,
        BusinessLevelPermission | BranchLevelPermission | GuardianObjectPermissions,
    ]

    def get_queryset(self):

        queryset = self.queryset

        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_BUSINESS_PAYMENT_METHOD.value[0]
            + "_business",
            self.request.business,
        ):
            queryset = queryset.filter(business=self.request.business)
        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_BUSINESS_PAYMENT_METHOD.value[0]
            + "_branch",
            self.request.branch,
        ):
            queryset = queryset.filter(branch=self.request.branch)
        else:
            queryset = queryset.none()

        return queryset


class PaymentMethodViewset(ListModelMixin, GenericViewSet):
    queryset = PaymentMethod.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentMethodSerializer


class AccountViewset(ListModelMixin, GenericViewSet):
    """Viewset that returns BusinessPaymentMethod as accounts."""

    queryset = BusinessPaymentMethod.objects.all()
    serializer_class = AccountSerializer
    permission_classes = [
        IsAuthenticated,
        BusinessLevelPermission | BranchLevelPermission | GuardianObjectPermissions,
    ]

    def get_queryset(self):
        queryset = self.queryset
        business = self.request.business
        branch = self.request.branch

        print(business, branch)

        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_BUSINESS_PAYMENT_METHOD.value[0]
            + "_business",
            business,
        ):
            queryset = queryset.filter(business=business)

        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_BUSINESS_PAYMENT_METHOD.value[0]
            + "_branch",
            branch,
        ):
            queryset = queryset.filter(branch=branch)
        else:
            queryset = queryset.none()

        return queryset


@api_view(["GET"])
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

    # Check permissions
    if not request.user.has_perm(
        AdditionalBusinessPermissionNames.CAN_VIEW_TRANSACTION.value[0] + "_business",
        business,
    ) and not (
        branch
        and request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_TRANSACTION.value[0] + "_branch",
            branch,
        )
    ):
        return Response(
            {"detail": "You do not have permission to view financial summary."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Base queryset filters
    transaction_filter = Q(business=business)
    order_filter = Q(business=business)

    if branch:
        transaction_filter &= Q(branch=branch)
        order_filter &= Q(branch=branch)

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
        sale_refund_total = pm_transactions.filter(
            type__in=[
                Transaction.TransactionType.SALE,
                Transaction.TransactionType.REFUND,
            ]
        ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
        expense_debt_total = pm_transactions.filter(
            type__in=[
                Transaction.TransactionType.EXPENSE,
                Transaction.TransactionType.DEBT,
            ]
        ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
        total_assets += sale_refund_total - expense_debt_total

    # Calculate total liabilities (sum of DEBT transactions' total_left_amount)
    total_liabilities = transactions.filter(
        type=Transaction.TransactionType.DEBT
    ).aggregate(total=Sum("total_left_amount"))["total"] or Decimal("0.00")

    # Net worth
    net_worth = total_assets - total_liabilities

    # Current month calculations
    current_month_transactions = transactions.filter(
        created_at__gte=current_month_start
    )
    monthly_income = current_month_transactions.filter(
        type=Transaction.TransactionType.SALE
    ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
    monthly_expense = current_month_transactions.filter(
        type=Transaction.TransactionType.EXPENSE
    ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
    monthly_cash_flow = monthly_income - monthly_expense
    monthly_profit = monthly_cash_flow  # Assuming profit = cash flow for now
    monthly_profit_margin = (
        (monthly_profit / monthly_income * 100)
        if monthly_income > 0
        else Decimal("0.00")
    )

    # Previous month calculations
    previous_month_transactions = transactions.filter(
        created_at__gte=previous_month_start, created_at__lte=previous_month_end
    )
    previous_month_income = previous_month_transactions.filter(
        type=Transaction.TransactionType.SALE
    ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
    previous_month_expense = previous_month_transactions.filter(
        type=Transaction.TransactionType.EXPENSE
    ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
    previous_month_profit = previous_month_income - previous_month_expense

    # Year to date calculations
    ytd_transactions = transactions.filter(created_at__gte=year_start)
    year_to_date_income = ytd_transactions.filter(
        type=Transaction.TransactionType.SALE
    ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
    year_to_date_expense = ytd_transactions.filter(
        type=Transaction.TransactionType.EXPENSE
    ).aggregate(total=Sum("total_paid_amount"))["total"] or Decimal("0.00")
    year_to_date_profit = year_to_date_income - year_to_date_expense

    # Pending receivables (SALE transactions with total_left_amount > 0)
    pending_receivables = transactions.filter(
        type=Transaction.TransactionType.SALE, total_left_amount__gt=0
    ).aggregate(total=Sum("total_left_amount"))["total"] or Decimal("0.00")

    # Pending payables (EXPENSE and DEBT transactions with total_left_amount > 0)
    pending_payables = transactions.filter(
        type__in=[
            Transaction.TransactionType.EXPENSE,
            Transaction.TransactionType.DEBT,
        ],
        total_left_amount__gt=0,
    ).aggregate(total=Sum("total_left_amount"))["total"] or Decimal("0.00")

    # Monthly transactions count
    monthly_transactions = current_month_transactions.count()

    # Orders counts
    orders = Order.objects.filter(order_filter)
    completed_orders = orders.filter(status=Order.StatusChoices.COMPLETED).count()
    pending_orders = orders.filter(status=Order.StatusChoices.PENDING).count()

    # Prepare summary data
    summary_data = {
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": net_worth,
        "monthly_income": monthly_income,
        "monthly_expense": monthly_expense,
        "monthly_cash_flow": monthly_cash_flow,
        "monthly_profit": monthly_profit,
        "monthly_profit_margin": monthly_profit_margin,
        "previous_month_income": previous_month_income,
        "previous_month_expense": previous_month_expense,
        "previous_month_profit": previous_month_profit,
        "year_to_date_income": year_to_date_income,
        "year_to_date_expense": year_to_date_expense,
        "year_to_date_profit": year_to_date_profit,
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
        price = item.variant.selling_price or Decimal("0")
        income_by_category[category_name] += item.quantity * price

    return dict(income_by_category)


def _get_expense_by_category(transaction_filter):
    """
    Aggregate expense transactions by their category field.
    Transactions with no category are grouped under 'Other'.
    """
    expense_transactions = Transaction.objects.filter(
        transaction_filter, type=Transaction.TransactionType.EXPENSE
    ).values("category", "total_paid_amount")

    expense_by_category = defaultdict(Decimal)
    for tx in expense_transactions:
        category_name = tx["category"] or "Other"
        expense_by_category[category_name] += tx["total_paid_amount"]

    return dict(expense_by_category)


def _month_range(year, month):
    """Return (start, end) datetime for a given year/month (UTC-aware)."""
    import calendar

    start = timezone.datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
    last_day = calendar.monthrange(year, month)[1]
    end = timezone.datetime(
        year, month, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc
    )
    return start, end


@api_view(["GET"])
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

    # Permission check
    if not request.user.has_perm(
        AdditionalBusinessPermissionNames.CAN_VIEW_TRANSACTION.value[0] + "_business",
        business,
    ) and not (
        branch
        and request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_TRANSACTION.value[0] + "_branch",
            branch,
        )
    ):
        return Response(
            {"detail": "You do not have permission to view financial reports."},
            status=status.HTTP_403_FORBIDDEN,
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

    # Base filters
    base_tx_filter = Q(business=business)
    base_order_filter = Q(
        order__business=business,
        order__status__in=[
            Order.StatusChoices.COMPLETED,
            Order.StatusChoices.PAID,
            Order.StatusChoices.PARTIALLY_PAID,
            Order.StatusChoices.DELIVERED,
        ],
    )
    if branch:
        base_tx_filter &= Q(branch=branch)
        base_order_filter &= Q(order__branch=branch)

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

    # Top income categories (sorted descending by amount)
    top_income = dict(
        sorted(monthly_income_by_category.items(), key=lambda x: x[1], reverse=True)
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

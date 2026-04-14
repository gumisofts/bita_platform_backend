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
from orders.models import Order

from .models import BusinessPaymentMethod, PaymentMethod, Transaction
from .serializers import (
    AccountSerializer,
    BusinessPaymentMethodSerializer,
    FinanceSummarySerializer,
    PaymentMethodSerializer,
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

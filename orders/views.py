from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction as db_transaction
from django.db.models import Count, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
)
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
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
from finances.models import Transaction
from inventories.models import Item, ItemVariant, SuppliedItem
from orders.filters import OrderFilter
from orders.models import Order, OrderItem
from orders.serializers import OrderItemSerializer, OrderListSerializer, OrderSerializer
from orders.signals import order_completed


class OrderItemViewset(ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    http_method_names = ["post"]
    permission_classes = [
        BusinessLevelPermission | BranchLevelPermission | GuardianObjectPermissions
    ]

    def create(self, request, *args, **kwargs):
        with db_transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Save the new OrderItem
            order_item = serializer.save()
            # Get the associated Order
            order = order_item.order

            # Get the latest supply price of the item
            latest_supply = (
                SuppliedItem.objects.filter(item=order_item.item)
                .order_by("-timestamp")
                .first()
            )

            if latest_supply:
                item_unit_price = latest_supply.price
            else:
                return Response(
                    {"error": "No supply record found for this item."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Update the order's total_payable field
            order.total_payable += item_unit_price * order_item.quantity
            order.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderViewset(ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    http_method_names = ["get", "post", "patch"]
    permission_classes = [
        BusinessLevelPermission | BranchLevelPermission | GuardianObjectPermissions
    ]
    filterset_class = OrderFilter

    def get_queryset(self):
        queryset = super().get_queryset()

        if not self.request.business:
            raise ValidationError({"detail": "Empty or invalid business"})

        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_ORDER.value[0] + "_business",
            self.request.business,
        ):
            queryset = queryset.filter(business=self.request.business)
        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_ORDER.value[0] + "_branch",
            self.request.branch,
        ):
            queryset = queryset.filter(branch=self.request.branch)
        else:
            queryset = queryset.none()
        return queryset.order_by("-created_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return OrderListSerializer
        return self.serializer_class

    def update(self, request, *args, **kwargs):
        order = self.get_object()
        previous_status = order.status

        response = super().update(request, *args, **kwargs)

        try:
            new_status = response.data.get("status")

            payment_method = request.data.get("payment_method")

            # If the status is changing to COMPLETED or PARTIALLY_PAID, ensure payment method is provided
            if new_status in [
                Order.StatusChoices.COMPLETED,
                Order.StatusChoices.PARTIALLY_PAID,
            ]:
                if not payment_method:
                    return Response(
                        {
                            "error": "Payment method is required when completing or partially paying an order."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Validate payment method against allowed choices
                if payment_method not in dict(Transaction.PaymentMethod.choices):
                    return Response(
                        {"error": "Invalid payment method."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Create a transaction if the status changed
                if previous_status != new_status:
                    with db_transaction.atomic():
                        transaction = Transaction.objects.create(
                            order=order,
                            type=Transaction.TransactionType.SALE,
                            # left 0 for lack of price value in inventory.Item object
                            total_paid_amount=0,
                            total_left_amount=0,
                            payment_method=payment_method,
                        )
                        transaction.save()

        except Exception as e:
            return Response(
                {"error": f"An unexpected error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return response

    @action(detail=True, methods=["get"])
    def checkout(self, request, *args, **kwargs):
        order = self.get_object()
        if order.status == Order.StatusChoices.COMPLETED:
            return Response(
                {"error": "Order is already completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order.status = Order.StatusChoices.COMPLETED
        order.save()
        order_completed.send(sender=Order, instance=order)
        return Response(OrderListSerializer(order).data, status=status.HTTP_200_OK)

    def _get_date_range_for_filter(self, filter_type):
        """Get date range based on filter type (today, this_week, this_year)"""
        now = timezone.now()

        if filter_type == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif filter_type == "this_week":
            # Start of week (Monday)
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = now
        elif filter_type == "this_year":
            start = now.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
            end = now
        else:
            raise ValidationError(
                {
                    "detail": f"Invalid filter type: {filter_type}. Use: today, this_week, this_year"
                }
            )

        return start, end

    @extend_schema(
        summary="Get best sellers",
        description="Returns a list of best selling items filtered by time period",
        parameters=[
            OpenApiParameter(
                name="filter",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Time filter: today, this_week, this_year",
                required=False,
                default="today",
            ),
            OpenApiParameter(
                name="limit",
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description="Number of results to return (default: 10)",
                required=False,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "filter": {"type": "string"},
                    "count": {"type": "integer"},
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "item_id": {"type": "string", "format": "uuid"},
                                "item_name": {"type": "string"},
                                "variant_id": {"type": "string", "format": "uuid"},
                                "variant_name": {"type": "string"},
                                "total_quantity_sold": {"type": "integer"},
                                "total_revenue": {"type": "number"},
                                "currency": {"type": "string"},
                            },
                        },
                    },
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def best_sellers(self, request):
        """
        Get best selling items filtered by time period

        Query parameters:
        - filter: Time filter (today, this_week, this_year). Default: today
        - limit: Number of results to return. Default: 10
        """
        # Get filter parameter
        filter_type = request.query_params.get("filter", "today")

        # Validate and parse limit parameter
        try:
            limit = int(request.query_params.get("limit", 10))
            if limit < 1:
                raise ValueError("Limit must be positive")
        except (ValueError, TypeError):
            return Response(
                {"detail": "Invalid limit parameter. Must be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate filter type
        try:
            start_date, end_date = self._get_date_range_for_filter(filter_type)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        # Get base queryset filtered by business/branch
        queryset = self.get_queryset()

        # Filter completed orders within date range
        completed_orders = queryset.filter(
            status=Order.StatusChoices.COMPLETED,
            created_at__gte=start_date,
            created_at__lte=end_date,
        )

        # Aggregate order items by variant and calculate metrics
        best_sellers = (
            OrderItem.objects.filter(order__in=completed_orders)
            .select_related("variant", "variant__item")
            .values(
                "variant__item__id",
                "variant__item__name",
                "variant__id",
                "variant__name",
            )
            .annotate(
                total_quantity_sold=Sum("quantity"),
                total_revenue=Sum(
                    F("quantity")
                    * Coalesce(F("variant__selling_price"), Value(Decimal("0")))
                ),
            )
            .order_by("-total_revenue", "-total_quantity_sold")[:limit]
        )

        # Format results
        results = []
        for seller in best_sellers:
            results.append(
                {
                    "item_id": str(seller["variant__item__id"]),
                    "item_name": seller["variant__item__name"],
                    "variant_id": str(seller["variant__id"]),
                    "variant_name": seller["variant__name"],
                    "total_quantity_sold": seller["total_quantity_sold"],
                    "total_revenue": float(seller["total_revenue"]),
                    "currency": "ETB",
                }
            )

        return Response(
            {
                "filter": filter_type,
                "count": len(results),
                "results": results,
            }
        )


class HomeStatsViewSet(GenericViewSet):
    """
    Home dashboard statistics endpoint
    """

    permission_classes = [
        BusinessLevelPermission | BranchLevelPermission | GuardianObjectPermissions
    ]
    queryset = Order.objects.all()

    def _get_business_and_branch(self):
        """Get business and branch from query params or request context"""
        # Try to get from query params first
        business_id = self.request.query_params.get(
            "business"
        ) or self.request.query_params.get("business_id")
        branch_id = self.request.query_params.get(
            "branch"
        ) or self.request.query_params.get("branch_id")

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
        elif self.request.business:
            # Fall back to middleware-set business
            business = self.request.business

        # Get branch from query params or middleware
        if branch_id:
            if not is_valid_uuid(branch_id):
                raise ValidationError({"detail": "Invalid branch ID format"})
            try:
                branch = Branch.objects.get(id=branch_id)
                # If business is set, ensure branch belongs to it
                if business and branch.business != business:
                    raise ValidationError(
                        {"detail": "Branch does not belong to the specified business"}
                    )
                # If business not set yet, use branch's business
                elif not business:
                    business = branch.business
            except Branch.DoesNotExist:
                raise ValidationError({"detail": "Branch not found"})
        elif self.request.branch:
            # Fall back to middleware-set branch
            branch = self.request.branch
            # If business is set, ensure branch belongs to it
            if business and branch.business != business:
                raise ValidationError(
                    {"detail": "Branch does not belong to the specified business"}
                )
            # If business not set yet, use branch's business
            elif not business:
                business = branch.business

        if not business:
            raise ValidationError(
                {
                    "detail": "Business is required. Provide 'business' or 'business_id' query parameter"
                }
            )

        return business, branch

    def _get_base_queryset(self):
        """Get base queryset filtered by business/branch"""
        business, branch = self._get_business_and_branch()

        base_filter = Q(business=business)

        if branch:
            # If branch is specified, filter by branch
            if self.request.user.has_perm(
                AdditionalBusinessPermissionNames.CAN_VIEW_ORDER.value[0] + "_branch",
                branch,
            ):
                base_filter = Q(branch=branch)
            elif not self.request.user.has_perm(
                AdditionalBusinessPermissionNames.CAN_VIEW_ORDER.value[0] + "_business",
                business,
            ):
                base_filter = Q(pk__in=[])  # No access

        # Store for use in other methods
        self._current_business = business
        self._current_branch = branch

        return base_filter

    def _get_date_range(self, range_type, start_date=None, end_date=None):
        """Get date range based on range type"""
        now = timezone.now()

        if range_type == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif range_type == "this_week":
            # Start of week (Monday)
            days_since_monday = now.weekday()
            start = (now - timedelta(days=days_since_monday)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            end = now
        elif range_type == "this_month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif range_type == "this_year":
            start = now.replace(
                month=1, day=1, hour=0, minute=0, second=0, microsecond=0
            )
            end = now
        elif range_type == "custom_range":
            if not start_date or not end_date:
                raise ValidationError(
                    {"detail": "start_date and end_date required for custom_range"}
                )
            try:
                start = timezone.make_aware(datetime.strptime(start_date, "%Y-%m-%d"))
                end = timezone.make_aware(datetime.strptime(end_date, "%Y-%m-%d"))
                end = end.replace(hour=23, minute=59, second=59, microsecond=999999)
            except ValueError:
                raise ValidationError({"detail": "Invalid date format. Use YYYY-MM-DD"})
        else:
            raise ValidationError({"detail": f"Invalid range type: {range_type}"})

        return start, end

    def _get_best_seller(self, base_filter):
        """Get best selling item by revenue"""
        # Get completed orders
        completed_orders = Order.objects.filter(
            base_filter, status=Order.StatusChoices.COMPLETED
        )

        # Aggregate order items by variant/item and calculate revenue (quantity * selling_price)
        # Use Coalesce to handle NULL selling_price values (treat as 0)
        best_seller = (
            OrderItem.objects.filter(order__in=completed_orders)
            .select_related("variant", "variant__item")
            .values("variant__item__id", "variant__item__name")
            .annotate(
                total_sales=Sum(
                    F("quantity")
                    * Coalesce(F("variant__selling_price"), Value(Decimal("0")))
                )
            )
            .order_by("-total_sales")
            .first()
        )

        if not best_seller:
            return {
                "itemId": None,
                "itemName": "N/A",
                "totalSales": 0,
                "currency": "ETB",
                "progressPercent": 0,
            }

        # Calculate progress percent (compare with second best seller)
        second_best = (
            OrderItem.objects.filter(order__in=completed_orders)
            .select_related("variant", "variant__item")
            .values("variant__item__id")
            .annotate(
                total_sales=Sum(
                    F("quantity")
                    * Coalesce(F("variant__selling_price"), Value(Decimal("0")))
                )
            )
            .order_by("-total_sales")
            .exclude(variant__item__id=best_seller["variant__item__id"])
            .first()
        )

        if second_best and second_best["total_sales"] > 0:
            progress_percent = int(
                (
                    best_seller["total_sales"]
                    / (best_seller["total_sales"] + second_best["total_sales"])
                )
                * 100
            )
        else:
            progress_percent = 100

        return {
            "itemId": str(best_seller["variant__item__id"]),
            "itemName": best_seller["variant__item__name"],
            "totalSales": float(best_seller["total_sales"]),
            "currency": "ETB",
            "progressPercent": progress_percent,
        }

    def _get_sales_distribution(
        self, base_filter, range_type, start_date=None, end_date=None
    ):
        """Get sales distribution by date"""
        start, end = self._get_date_range(range_type, start_date, end_date)

        completed_orders = Order.objects.filter(
            base_filter,
            status=Order.StatusChoices.COMPLETED,
            created_at__gte=start,
            created_at__lte=end,
        )

        if range_type == "this_week":
            # Group by day of week
            from django.db.models.functions import TruncDate

            sales_by_day = (
                completed_orders.annotate(date=TruncDate("created_at"))
                .values("date")
                .annotate(total=Sum("total_payable"))
                .order_by("date")
            )

            # Convert to dictionary for easy lookup
            sales_dict = {item["date"]: float(item["total"]) for item in sales_by_day}

            # Map to day labels
            day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            data = []

            # Get all days in the week
            current = start
            while current <= end:
                weekday = current.weekday()  # 0=Monday, 6=Sunday
                date_key = current.date()
                data.append(
                    {"label": day_labels[weekday], "value": sales_dict.get(date_key, 0)}
                )
                current += timedelta(days=1)

            return {"range": range_type, "data": data}
        elif range_type == "this_month":
            # Group by day
            from django.db.models.functions import TruncDate

            sales_by_day = (
                completed_orders.annotate(date=TruncDate("created_at"))
                .values("date")
                .annotate(total=Sum("total_payable"))
                .order_by("date")
            )

            # Convert to dictionary for easy lookup
            sales_dict = {item["date"]: float(item["total"]) for item in sales_by_day}

            data = []
            current = start
            while current <= end:
                date_key = current.date()
                data.append(
                    {
                        "label": current.strftime("%d"),
                        "value": sales_dict.get(date_key, 0),
                    }
                )
                current += timedelta(days=1)

            return {"range": range_type, "data": data}
        elif range_type == "this_year":
            # Group by month
            from django.db.models.functions import TruncMonth

            sales_by_month = (
                completed_orders.annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(total=Sum("total_payable"))
                .order_by("month")
            )

            # Convert to dictionary for easy lookup
            sales_dict = {}
            for item in sales_by_month:
                month_key = (item["month"].year, item["month"].month)
                sales_dict[month_key] = float(item["total"])

            month_labels = [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ]
            data = []

            current = start
            while current <= end:
                month_key = (current.year, current.month)
                data.append(
                    {
                        "label": month_labels[current.month - 1],
                        "value": sales_dict.get(month_key, 0),
                    }
                )
                # Move to next month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1)
                else:
                    current = current.replace(month=current.month + 1)

            return {"range": range_type, "data": data}
        else:  # custom_range
            # Group by day for custom range
            from django.db.models.functions import TruncDate

            sales_by_day = (
                completed_orders.annotate(date=TruncDate("created_at"))
                .values("date")
                .annotate(total=Sum("total_payable"))
                .order_by("date")
            )

            # Convert to dictionary for easy lookup
            sales_dict = {item["date"]: float(item["total"]) for item in sales_by_day}

            data = []
            current = start
            while current <= end:
                date_key = current.date()
                data.append(
                    {
                        "label": current.strftime("%m/%d"),
                        "value": sales_dict.get(date_key, 0),
                    }
                )
                current += timedelta(days=1)

            return {"range": range_type, "data": data}

    def _get_summary(self, base_filter, range_type, start_date=None, end_date=None):
        """Get summary statistics"""
        start, end = self._get_date_range(range_type, start_date, end_date)

        # Total sales from completed orders
        completed_orders = Order.objects.filter(
            base_filter,
            status=Order.StatusChoices.COMPLETED,
            created_at__gte=start,
            created_at__lte=end,
        )
        total_sales = completed_orders.aggregate(total=Sum("total_payable"))[
            "total"
        ] or Decimal("0")

        # Low stock items (quantity <= notify_below)
        items_queryset = Item.objects.filter(business=self._current_business)
        if self._current_branch:
            items_queryset = items_queryset.filter(branch=self._current_branch)

        low_stock_items = items_queryset.filter(quantity__lte=F("notify_below")).count()

        # Items expiring (within next 30 days)
        from datetime import date

        expiry_threshold = date.today() + timedelta(days=30)
        expiring_items_queryset = SuppliedItem.objects.filter(
            business=self._current_business,
            expire_date__isnull=False,
            expire_date__lte=expiry_threshold,
            expire_date__gte=date.today(),
            quantity__gt=0,
        )
        if self._current_branch:
            # Filter by branch through the supply relationship
            expiring_items_queryset = expiring_items_queryset.filter(
                supply__branch=self._current_branch
            )
        expiring_items = expiring_items_queryset.values("item").distinct().count()

        # Sales logged (number of completed orders)
        sales_logged = completed_orders.count()

        return {
            "range": range_type,
            "total_sales": {"value": float(total_sales), "currency": "ETB"},
            "low_stock_items": low_stock_items,
            "items_expiring": expiring_items,
            "sales_logged": sales_logged,
        }

    @extend_schema(
        summary="Get home dashboard statistics",
        description="Returns best seller, sales distribution, and summary statistics for the dashboard",
        parameters=[
            OpenApiParameter(
                name="business",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="Business ID (UUID). Can also use 'business_id'",
                required=False,
            ),
            OpenApiParameter(
                name="branch",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.QUERY,
                description="Branch ID (UUID). Can also use 'branch_id'",
                required=False,
            ),
            OpenApiParameter(
                name="sales-distribution-range",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Range for sales distribution: this_week, this_month, this_year, custom_range",
                required=False,
            ),
            OpenApiParameter(
                name="summary-range",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Range for summary stats: today, this_week, this_month, this_year",
                required=False,
            ),
            OpenApiParameter(
                name="start_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="Start date for custom_range (format: YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                name="end_date",
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description="End date for custom_range (format: YYYY-MM-DD)",
                required=False,
            ),
        ],
        responses={
            200: {
                "type": "object",
                "properties": {
                    "bestSeller": {
                        "type": "object",
                        "properties": {
                            "itemId": {"type": "string"},
                            "itemName": {"type": "string"},
                            "totalSales": {"type": "integer"},
                            "currency": {"type": "string"},
                            "progressPercent": {"type": "integer"},
                        },
                    },
                    "salesDistribution": {
                        "type": "object",
                        "properties": {
                            "range": {"type": "string"},
                            "data": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "label": {"type": "string"},
                                        "value": {"type": "number"},
                                    },
                                },
                            },
                        },
                    },
                    "summary": {
                        "type": "object",
                        "properties": {
                            "range": {"type": "string"},
                            "total_sales": {
                                "type": "object",
                                "properties": {
                                    "value": {"type": "number"},
                                    "currency": {"type": "string"},
                                },
                            },
                            "lowStockItems": {"type": "integer"},
                            "itemsExpiring": {"type": "integer"},
                            "sales_logged": {"type": "integer"},
                        },
                    },
                },
            }
        },
    )
    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Get home dashboard statistics

        Query parameters:
        - business or business_id: Business UUID (required if not set by middleware)
        - branch or branch_id: Branch UUID (optional)
        - sales-distribution-range: this_week, this_month, this_year, custom_range
        - summary-range: today, this_week, this_month, this_year
        - start_date: YYYY-MM-DD (required for custom_range)
        - end_date: YYYY-MM-DD (required for custom_range)
        """
        try:
            base_filter = self._get_base_queryset()
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        # Get query parameters
        sales_distribution_range = request.query_params.get(
            "sales-distribution-range", "this_week"
        )
        summary_range = request.query_params.get("summary-range", "today")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # Get best seller
        best_seller = self._get_best_seller(base_filter)

        # Get sales distribution
        try:
            sales_distribution = self._get_sales_distribution(
                base_filter, sales_distribution_range, start_date, end_date
            )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        # Get summary
        try:
            summary = self._get_summary(
                base_filter, summary_range, start_date, end_date
            )
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "best_seller": best_seller,
                "sales_distribution": sales_distribution,
                "summary": summary,
            }
        )

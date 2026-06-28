from decimal import Decimal

from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from business.models import Employee
from inventories.models import ItemVariant, SuppliedItem
from orders.models import Order, OrderItem, OrderReturn, OrderReturnItem


class CurrentEmployeeDefault(serializers.CurrentUserDefault):
    requires_context = True

    def __call__(self, serializer_field):
        business = serializer_field.context["request"].business
        employee = Employee.objects.filter(
            user=serializer_field.context["request"].user, business=business
        ).first()
        return employee


class CurrentBranchDefault(serializers.CurrentUserDefault):
    requires_context = True

    def __call__(self, serializer_field):
        branch = serializer_field.context["request"].branch
        return branch


class CurrentBusinessDefault(serializers.CurrentUserDefault):
    requires_context = True

    def __call__(self, serializer_field):
        business = serializer_field.context["request"].business
        return business


class OrderSerializer(ModelSerializer):
    employee = serializers.HiddenField(default=CurrentEmployeeDefault())
    customer_name = serializers.CharField(read_only=True, source="customer.full_name")
    employee_name = serializers.CharField(read_only=True, source="employee.full_name")
    items_display_name = serializers.SerializerMethodField()
    business = serializers.HiddenField(default=CurrentBusinessDefault())
    branch = serializers.HiddenField(default=CurrentBranchDefault())

    def get_items_display_name(self, obj):
        return ", ".join([item.variant.item.name for item in obj.items.all()])

    class InternalOrderItemSerializer(ModelSerializer):
        price = serializers.DecimalField(
            max_digits=12, decimal_places=2, required=False, allow_null=True
        )

        class Meta:
            model = OrderItem
            exclude = ["order"]

    item_variants = InternalOrderItemSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = "__all__"

    def validate(self, attrs):
        business = self.context["request"].business
        branch = self.context["request"].branch
        if not business:
            raise serializers.ValidationError({"detail": "Business is required"})
        if not branch:
            raise serializers.ValidationError({"detail": "Branch is required"})

        for entry in attrs.get("item_variants", []):
            variant = entry.get("variant")
            if variant is None:
                continue
            if variant.item.branch_id != branch.id:
                raise serializers.ValidationError(
                    {"detail": "One or more variants are not in the branch"}
                )
        return super().validate(attrs)

    def _resolve_item_price(self, item_variant):
        """Resolve price: request price > supplied_item.selling_price."""
        price = item_variant.get("price")
        if not price:
            supplied_item = item_variant.get("supplied_item")
            if supplied_item:
                price = supplied_item.selling_price
        return price

    def create(self, validated_data):
        item_variants = validated_data.pop("item_variants", [])

        order = Order.objects.create(**validated_data)
        total_payable = Decimal("0")
        for item_variant in item_variants:
            item_variant["price"] = self._resolve_item_price(item_variant)
            OrderItem.objects.create(order=order, **item_variant)
            total_payable += (item_variant.get("price") or Decimal("0")) * item_variant[
                "quantity"
            ]
        order.total_payable = total_payable
        order.save(update_fields=["total_payable"])
        return order

    def update(self, instance, validated_data):
        item_variants = validated_data.pop("item_variants", [])
        instance = super().update(instance, validated_data)
        for item_variant in item_variants:
            item_variant["price"] = self._resolve_item_price(item_variant)
            OrderItem.objects.create(order=instance, **item_variant)
            instance.total_payable = (instance.total_payable or Decimal("0")) + (
                (item_variant.get("price") or Decimal("0")) * item_variant["quantity"]
            )
        if item_variants:
            instance.save(update_fields=["total_payable"])
        return instance


class SuppliedItemSummarySerializer(ModelSerializer):
    class Meta:
        model = SuppliedItem
        fields = [
            "id",
            "batch_number",
            "product_number",
            "selling_price",
            "purchase_price",
            "expire_date",
            "man_date",
            "quantity",
            "initial_quantity",
            "is_returnable",
            "is_visible_online",
        ]


class VariantSummarySerializer(ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_id = serializers.UUIDField(source="item.id", read_only=True)

    class Meta:
        model = ItemVariant
        fields = ["id", "name", "sku", "quantity", "is_default", "item_id", "item_name"]


class OrderItemDetailSerializer(ModelSerializer):
    variant = VariantSummarySerializer(read_only=True)
    supplied_item = SuppliedItemSummarySerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "variant", "supplied_item", "quantity", "price", "created_at"]


class OrderListSerializer(ModelSerializer):
    items = OrderItemDetailSerializer(many=True, read_only=True)
    employee_name = serializers.CharField(read_only=True, source="employee.full_name")
    customer_name = serializers.CharField(read_only=True, source="customer.full_name")
    receipt_url = serializers.SerializerMethodField()

    def get_receipt_url(self, obj):
        if not obj.receipt:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.receipt.url)
        return obj.receipt.url

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "customer",
            "customer_name",
            "employee",
            "employee_name",
            "business",
            "branch",
            "payment_method",
            "transaction_id",
            "total_payable",
            "receipt_url",
            "additional_info",
            "items",
            "created_at",
            "updated_at",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )

    class Meta:
        model = OrderItem
        fields = "__all__"


class OrderReturnItemInputSerializer(serializers.Serializer):
    order_item_id = serializers.UUIDField()
    quantity_returned = serializers.IntegerField(min_value=1)


class OrderReturnCreateSerializer(serializers.Serializer):
    items = OrderReturnItemInputSerializer(many=True, min_length=1)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    refund_method = serializers.UUIDField(
        required=False,
        allow_null=True,
        default=None,
        help_text="BusinessPaymentMethod UUID for the refund",
    )


class OrderReturnItemReadSerializer(ModelSerializer):
    variant_name = serializers.CharField(
        source="order_item.variant.name", read_only=True
    )
    item_name = serializers.CharField(
        source="order_item.variant.item.name", read_only=True
    )

    class Meta:
        model = OrderReturnItem
        fields = [
            "id",
            "order_item",
            "variant_name",
            "item_name",
            "quantity_returned",
            "is_restocked",
            "refund_amount",
        ]


class OrderReturnReadSerializer(ModelSerializer):
    items = OrderReturnItemReadSerializer(many=True, read_only=True)
    processed_by_name = serializers.CharField(
        source="processed_by.full_name", read_only=True
    )

    class Meta:
        model = OrderReturn
        fields = [
            "id",
            "order",
            "status",
            "reason",
            "refund_method",
            "total_refund_amount",
            "processed_by",
            "processed_by_name",
            "items",
            "created_at",
        ]

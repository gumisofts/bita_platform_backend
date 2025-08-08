from rest_framework import serializers

from business.models import Branch
from inventories.models import *

from .models import Item

# Category, Store, Supply, Location, StockMovement, ReturnRecall, ItemImage, SupplyReservation


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__"


class PropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        exclude = []
        read_only_fields = ["id", "created_at", "updated_at"]


class SuppliedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuppliedItem
        exclude = []
        read_only_fields = ["id", "created_at", "updated_at"]


class SupplySerializer(serializers.ModelSerializer):
    class SuppliedItemSerializer(serializers.ModelSerializer):
        class Meta:
            model = SuppliedItem
            exclude = ["business"]
            read_only_fields = ["id", "created_at", "updated_at"]

    item = SuppliedItemSerializer(required=False)

    class Meta:
        model = Supply
        exclude = []

    def create(self, validated_data):
        item = validated_data.pop("item", None)

        supply = super().create(validated_data)

        if item:
            SuppliedItem.objects.create(supply=supply, business=supply.business, **item)

        return supply


class PricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pricing
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ReturnRecallSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnRecall
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class ItemVariantSerializer(serializers.ModelSerializer):

    class PricingSerializer(serializers.ModelSerializer):

        class Meta:
            model = Pricing
            exclude = ["item_variant"]
            read_only_fields = ["id", "created_at", "updated_at"]

    class PropertySerializer(serializers.ModelSerializer):
        class Meta:
            model = Property
            exclude = ["item_variant"]
            read_only_fields = ["id", "created_at", "updated_at"]

    class Meta:
        model = ItemVariant
        exclude = []
        read_only_fields = ["id", "selling_price", "created_at", "updated_at"]

    properties = PropertySerializer(many=True, required=False)
    pricings = PricingSerializer(many=True, required=False)

    def create(self, validated_data):
        properties = validated_data.pop("properties", [])
        pricings = validated_data.pop("pricings", [])
        instance = super().create(validated_data)
        for property in properties:
            Property.objects.create(item_variant=instance, **property)
        for pricing in pricings:
            Pricing.objects.create(item_variant=instance, **pricing)
        return instance

    def update(self, instance, validated_data):
        properties = validated_data.pop("properties", [])
        pricings = validated_data.pop("pricings", [])
        instance = super().update(instance, validated_data)
        Property.objects.filter(item_variant=instance).delete()
        Pricing.objects.filter(item_variant=instance).delete()
        for property in properties:
            Property.objects.create(item_variant=instance, **property)
        for pricing in pricings:
            Pricing.objects.create(item_variant=instance, **pricing)
        return instance


class InventoryMovementItemSerializer(serializers.ModelSerializer):
    supplied_item_details = serializers.SerializerMethodField(read_only=True)

    def get_supplied_item_details(self, obj):
        return {
            "item_name": obj.supplied_item.item.name,
            "batch_number": obj.supplied_item.batch_number,
            "product_number": obj.supplied_item.product_number,
            "available_quantity": obj.supplied_item.quantity,
        }

    class Meta:
        model = InventoryMovementItem
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class InventoryMovementSerializer(serializers.ModelSerializer):
    movement_items = InventoryMovementItemSerializer(many=True, read_only=True)
    from_branch_name = serializers.CharField(source="from_branch.name", read_only=True)
    to_branch_name = serializers.CharField(source="to_branch.name", read_only=True)
    requested_by_name = serializers.CharField(
        source="requested_by.get_full_name", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = InventoryMovement
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "movement_number",
            "approved_by",
            "shipped_by",
            "received_by",
            "approved_at",
            "shipped_at",
            "received_at",
        ]

    def validate(self, attrs):
        from_branch = attrs.get("from_branch")
        to_branch = attrs.get("to_branch")

        if from_branch == to_branch:
            raise serializers.ValidationError(
                "From branch and to branch cannot be the same"
            )

        # Ensure both branches belong to the same business
        if from_branch.business != to_branch.business:
            raise serializers.ValidationError(
                "Both branches must belong to the same business"
            )

        # Set business from branches
        attrs["business"] = from_branch.business

        return attrs


class InventoryMovementCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating inventory movements with items"""

    items = serializers.ListField(child=serializers.DictField(), write_only=True)

    class Meta:
        model = InventoryMovement
        fields = ["id", "from_branch", "to_branch", "notes", "items"]

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("At least one item must be specified")

        for item in items:
            if "supplied_item_id" not in item or "quantity" not in item:
                raise serializers.ValidationError(
                    "Each item must have 'supplied_item_id' and 'quantity'"
                )

            if item["quantity"] <= 0:
                raise serializers.ValidationError("Quantity must be greater than 0")

        return items

    def validate(self, attrs):
        from_branch = attrs.get("from_branch")
        to_branch = attrs.get("to_branch")

        if from_branch == to_branch:
            raise serializers.ValidationError(
                "From branch and to branch cannot be the same"
            )

        # Ensure both branches belong to the same business
        if from_branch.business != to_branch.business:
            raise serializers.ValidationError(
                "Both branches must belong to the same business"
            )

        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        user = self.context["request"].user

        # Set business and requested_by
        validated_data["business"] = validated_data["from_branch"].business
        validated_data["requested_by"] = user

        movement = InventoryMovement.objects.create(**validated_data)

        # Create movement items
        for item_data in items_data:
            try:
                supplied_item = SuppliedItem.objects.get(
                    id=item_data["supplied_item_id"],
                    supply__branch=movement.from_branch,
                )

                # Check if requested quantity is available
                if item_data["quantity"] > supplied_item.quantity:
                    raise serializers.ValidationError(
                        f"Requested quantity ({item_data['quantity']}) exceeds available quantity ({supplied_item.quantity}) for {supplied_item.item.name}"
                    )

                InventoryMovementItem.objects.create(
                    movement=movement,
                    supplied_item=supplied_item,
                    quantity_requested=item_data["quantity"],
                    notes=item_data.get("notes", ""),
                    variant_id=item_data.get("variant", None),
                )
            except SuppliedItem.DoesNotExist:
                raise serializers.ValidationError(
                    f"Supplied item with ID {item_data['supplied_item_id']} not found in source branch"
                )

        return movement


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        exclude = []
        read_only_fields = ["id", "created_at", "updated_at"]

from rest_framework import serializers

from inventories.models import *

from .models import Item

# Category, Store, Supply, Location, StockMovement, ReturnRecall, ItemImage, SupplyReservation


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__"


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
    class Meta:
        model = ItemVariant
        exclude = []
        read_only_fields = ["id", "created_at", "updated_at"]

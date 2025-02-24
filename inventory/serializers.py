from rest_framework import serializers
from .models import (
    Category,
    Item,
    Location,
    ReturnRecall,
    StockMovement,
    Supply,
    Store,
    ItemImage,
    SupplyReservation,
)
from .utils import upload_to_file_service, validate_image_file


class CategorySerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "description", "item_count"]


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = [
            "id",
            "name",
            "description",
            "category",
            "manufacturer",
            "barcode",
            "is_returnable",
            "notify_below",
            "isvisible",
        ]


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "name", "business_id", "location"]


class SupplySerializer(serializers.ModelSerializer):

    class Meta:
        model = Supply
        fields = [
            "id",
            "item",
            "quantity",
            "unit",
            "cost_price",
            "sale_price",
            "expiration_date",
            "batch_number",
            "man_date",
            "store",
            "supplier_id",
        ]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = "__all__"


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ["id", "supply", "from_store", "to_store", "quantity", "reason"]


class ReturnRecallSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnRecall
        fields = ["id", "item", "quantity", "reason", "status"]


class ItemImageSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True)

    class Meta:
        model = ItemImage
        fields = ["id", "item", "image_id", "file"]
        read_only_fields = ["image_id"]
        extra_kwargs = {
            "file": {"write_only": True},
        }

    def validate_file(self, value):
        validate_image_file(value)
        return value

    def create(self, validated_data):

        file = validated_data.pop("file")

        file_id = upload_to_file_service(file)

        item_image = ItemImage.objects.create(file_id=file_id, **validated_data)

        return item_image


class SupplyReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplyReservation
        fields = ["id", "supply", "quantity", "reserved_at", "status"]

    def validate(self, data):
        supply = data.get("supply")
        quantity = data.get("quantity")
        if supply and quantity and quantity > supply.quantity:
            raise serializers.ValidationError(
                {
                    "quantity": "Reservation quantity cannot exceed available supply quantity."
                }
            )
        return data

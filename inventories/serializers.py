from rest_framework import serializers

from inventories.models import *

from .models import Item

# Category, Store, Supply, Location, StockMovement, ReturnRecall, ItemImage, SupplyReservation


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__"

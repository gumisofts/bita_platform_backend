from rest_framework import serializers
from .models import SuppliedItem,Supply
class SuppliedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuppliedItem
        fields = '__all__'

class SupplySerializer(serializers.ModelSerializer):
    supplied_items = SuppliedItemSerializer(many=True, read_only=True)

    class Meta:
        model = Supply
        fields = '__all__'
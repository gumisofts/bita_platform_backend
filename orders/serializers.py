from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from orders.models import *


class OrderSerializer(ModelSerializer):
    class InternalOrderItemSerializer(ModelSerializer):
        class Meta:
            model = OrderItem
            exclude = ["order"]

    item_variants = InternalOrderItemSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = "__all__"

    def create(self, validated_data):
        item_variants = validated_data.pop("item_variants", [])

        order = Order.objects.create(**validated_data)
        for item_variant in item_variants:
            OrderItem.objects.create(order=order, **item_variant)
        return order

    def update(self, instance, validated_data):
        item_variants = validated_data.pop("item_variants", [])
        instance = super().update(instance, validated_data)
        for item_variant in item_variants:
            OrderItem.objects.create(order=instance, **item_variant)
        return instance


class OrderListSerializer(ModelSerializer):
    class Meta:
        model = Order
        fields = "__all__"
        depth = 1


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = "__all__"

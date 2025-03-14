from rest_framework import serializers

from .models import BusinessPaymentMethod, Order, OrderItem, Transaction


class OrderSerializer(serializers.ModelSerializer):
    # id = serializers.UUIDField(format="hex")

    class Meta:
        model = Order
        fields = "__all__"


class OrderItemSerializer(serializers.ModelSerializer):
    # id = serializers.UUIDField(format="hex")

    class Meta:
        model = OrderItem
        fields = "__all__"


class TransactionSerializer(serializers.ModelSerializer):
    # id = serializers.UUIDField(format="hex")

    class Meta:
        model = Transaction
        fields = "__all__"


class PaymentMethodSerializer(serializers.Serializer):
    key = serializers.CharField()
    value = serializers.CharField()


class BusinessPaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessPaymentMethod
        fields = "__all__"

from rest_framework import serializers

from finances.models import BusinessPaymentMethod, PaymentMethod, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        exclude = []


class BusinessPaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessPaymentMethod
        exclude = []

from rest_framework import serializers

from financials.models import BusinessPaymentMethod, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessPaymentMethod
        exclude = []


class BusinessPaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessPaymentMethod
        exclude = []

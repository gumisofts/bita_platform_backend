from rest_framework import serializers

from finances.models import BusinessPaymentMethod, PaymentMethod, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = "__all__"
        depth = 1


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        exclude = []


class BusinessPaymentMethodSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)

    class Meta:
        model = BusinessPaymentMethod
        exclude = []
        extra_kwargs = {
            "label": {"required": False, "allow_blank": True},
            "identifier": {"required": False, "allow_blank": True},
        }

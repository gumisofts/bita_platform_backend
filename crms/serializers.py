from django.core.exceptions import ValidationError
from rest_framework import serializers

from .models import *


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "email", "full_name", "business", "phone_number", "created_at"]
        read_only_fields = ["id", "created_at"]


# class GiftCardTransactionSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = GiftCardTransaction
#         fields = ["id", "amount", "description", "created_at"]
#         read_only_fields = ["id", "created_at"]

#     def create(self, validated_data):
#         amount = validated_data.pop("amount")
#         remaining_value = GiftCard.objects.get(remaining_value=remaining_value)
#         original_value = GiftCard.objects.get(original_value=original_value)

#         if GiftCard.status == "used":
#             raise ValidationError["Already used card"]


# class GiftCardSerializer(serializers.ModelSerializer):
#     customer = CustomerSerializer(read_only=True)
#     transaction = GiftCardTransactionSerializer(many=True, read_only=True)

#     class Meta:
#         model = GiftCard
#         fields = "__all__"

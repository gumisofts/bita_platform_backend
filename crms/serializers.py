from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Customer, GiftCard, GiftCardTransfer

User = get_user_model()


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "email", "full_name", "business", "phone_number", "created_at"]
        read_only_fields = ["id", "created_at"]


class GiftCardSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer(read_only=True)
    amount = serializers.IntegerField(write_only=True, min_value=1)
    issued_by_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = GiftCard
        exclude = ["created_by", "created_at", "updated_at"]
        read_only_fields = ["id", "issued_by", "created_at"]

    def validate_issued_by_id(self, value):

        try:
            user = User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("Issued_by user does not exist.")
        return user

    def create(self, validated_data):
        amount = validated_data.pop("amount")
        issued_by = validated_data.pop("issued_by_id")
        created_by = self.context["request"].user

        gift_cards = []
        for _ in range(int(amount)):
            giftcard = GiftCard.objects.create(
                **validated_data, created_by=created_by, issued_by=issued_by
            )
            gift_cards.append(giftcard)

        return gift_cards


class GiftCardTransferSerializer(serializers.ModelSerializer):
    gift_card_id = serializers.UUIDField()
    to_customer_id = serializers.IntegerField(write_only=True)
    from_customer_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = GiftCardTransfer
        fields = "__all__"
        read_only_fields = [
            "gift_card",
            "from_customer",
            "to_customer",
            "transferred_at",
        ]

    def validate(self, attrs):
        user = self.context["request"].user
        gift_card_id = attrs.get("gift_card_id")
        to_customer_id = attrs.get("customer_id")
        from_customer_id = attrs.get("from_customer_id")

        try:
            gift_card = GiftCard.objects.get(id=gift_card_id)
        except GiftCard.DoesNotExist:
            raise serializers.ValidationError("Gift Card does not exist")

        try:
            to_customer = Customer.objects.get(id=to_customer_id)
        except Customer.DoesNotExist:
            raise serializers.ValidationError("customer does not exist")

        try:
            from_customer = Customer.objects.get(id=from_customer)
        except Customer.DoesNotExist:
            raise serializers.ValidationError("Customer does not exist")

        if gift_card.current_owner != from_customer:
            raise serializers.ValidationError("This customer does not own gift card")

        attrs["gift_card"] = gift_card
        attrs["to_customer"] = to_customer
        attrs["from_customer"] = from_customer

        return attrs

    def create(self, validated_data):

        gift_card = validated_data["gift_card"]
        to_customer = validated_data["to_customer"]
        from_customer = validated_data["from_customer"]

        gift_card.current_owner = to_customer
        gift_card.save()

        return GiftCardTransfer.objects.create(
            gift_card=gift_card,
            from_customer=from_customer,
            to_customer=to_customer,
        )

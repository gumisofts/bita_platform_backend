from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import FAQ, Contact, Download, Plan, Waitlist


class PlanSerializer(serializers.ModelSerializer):
    features = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="name",
    )

    class Meta:
        model = Plan
        fields = ["id", "name", "price", "currency", "billing_period", "features"]
        read_only_fields = ["id"]

    def validate_price(self, value: str) -> str:
        if value is None:
            raise serializers.ValidationError("Price is required.")
        value = str(value).strip()
        import re

        if not re.fullmatch(r"\d+(\.\d{1,2})?", value):
            raise serializers.ValidationError(
                "Price must be a number with up to 2 decimal places."
            )
        return value

    def validate_currency(self, value: str) -> str:
        if value is None:
            return value
        value = str(value).strip()
        return value.upper()

    def validate_billing_period(self, value: str) -> str:
        if value is None:
            return value
        return str(value).strip()


class DownloadSerializer(serializers.ModelSerializer):
    icon = serializers.ImageField(required=False, allow_null=True)
    file = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Download
        fields = ["id", "platform", "icon", "file"]
        read_only_fields = ["id"]


class WaitlistSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        validators=[
            UniqueValidator(
                queryset=Waitlist.objects.all(),
                message="This email is already in the waitlist.",
            )
        ]
    )
    message = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Waitlist
        fields = ["id", "email", "created_at", "message"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        instance = Waitlist.objects.create(**validated_data)
        return instance

    def get_message(self, obj):
        return "added to waitlist"


class FAQSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQ
        fields = ["id", "question", "answer"]
        read_only_fields = ["id"]


class ContactSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    company = serializers.CharField(
        max_length=100, required=False, allow_blank=True, allow_null=True
    )
    message = serializers.CharField()

    class Meta:
        model = Contact
        fields = ["id", "name", "email", "company", "message", "received_at"]
        read_only_fields = ["id", "received_at"]

    def validate_message(self, value: str) -> str:
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError(
                "Message must be at least 10 characters long."
            )
        return value.strip()

    def create(self, validated_data):
        contact = Contact.objects.create(**validated_data)
        return contact

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance and getattr(instance, "pk", None):
            data.setdefault(
                "message",
                "Your message has been received. We will contact you soon.",
            )
        return data

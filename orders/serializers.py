from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from business.models import Employee
from orders.models import *


class CurrentEmployeeDefault(serializers.CurrentUserDefault):
    requires_context = True

    def __call__(self, serializer_field):
        business = serializer_field.context["request"].business
        employee = Employee.objects.filter(
            user=serializer_field.context["request"].user, business=business
        ).first()
        return employee


class CurrentBranchDefault(serializers.CurrentUserDefault):
    requires_context = True

    def __call__(self, serializer_field):
        branch = serializer_field.context["request"].branch
        return branch


class CurrentBusinessDefault(serializers.CurrentUserDefault):
    requires_context = True

    def __call__(self, serializer_field):
        business = serializer_field.context["request"].business
        return business


class OrderSerializer(ModelSerializer):
    employee = serializers.HiddenField(default=CurrentEmployeeDefault())
    customer_name = serializers.CharField(read_only=True, source="customer.full_name")
    employee_name = serializers.CharField(read_only=True, source="employee.full_name")
    business = serializers.HiddenField(default=CurrentBusinessDefault())
    branch = serializers.HiddenField(default=CurrentBranchDefault())

    class InternalOrderItemSerializer(ModelSerializer):
        class Meta:
            model = OrderItem
            exclude = ["order"]

    item_variants = InternalOrderItemSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = "__all__"

    def validate(self, attrs):
        business = self.context["request"].business
        branch = self.context["request"].branch
        print(attrs)
        if not business:
            raise serializers.ValidationError({"detail": "Business is required"})
        if not branch:
            raise serializers.ValidationError({"detail": "Branch is required"})

        variants = map(lambda x: x.get("variant"), attrs.get("item_variants", []))

        for variant in variants:
            if variant.item.branch != branch:
                raise serializers.ValidationError(
                    {"detail": "One or more variants are not in the branch"}
                )
        return super().validate(attrs)

        return attrs

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
    class InternalOrderItemSerializer(ModelSerializer):
        class Meta:
            model = OrderItem
            exclude = ["order"]
            depth = 1

    items = InternalOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = "__all__"
        depth = 1


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = "__all__"

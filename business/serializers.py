from rest_framework import serializers
from django.contrib.auth import get_user_model

from business.models import *
from django.db.models import Q
from rest_framework.exceptions import ValidationError


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class RoleSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()

    def get_permissions(self, obj):

        return map(lambda x: x.codename, obj.permissions.all())

    class Meta:
        model = Role
        fields = "__all__"


class BranchSerializer(serializers.ModelSerializer):
    current_user_role = serializers.SerializerMethodField()

    def get_current_user_role(self, obj):

        employee = Employee.objects.filter(
            Q(branch=obj) | Q(branch=None),
            user=self.context.get("request").user,
            business=obj.business,
        ).first()

        if not employee:
            return None

        return employee.role.id if employee.role else None

    class Meta:
        model = Branch
        fields = "__all__"


class BusinessSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    address = AddressSerializer()

    class Meta:
        model = Business
        fields = "__all__"

    def create(self, validated_data):
        address = validated_data.pop("address")
        address = Address.objects.create(**address)
        validated_data["address"] = address
        return super().create(validated_data)


class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        exclude = []


class BusinessImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessImage
        exclude = []


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        exclude = []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        lat = attrs.get("lat")
        lng = attrs.get("lng")

        errors = {}

        if lat < -90 or lat > 90:
            errors["lat"] = "latitude should be between -90 and 90"

        if lng < -180 or lng > 180:
            errors["lng"] = "longitude should be between -180 and 180"

        if errors:
            raise ValidationError(errors)

        return attrs

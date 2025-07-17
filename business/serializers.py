import re

from django.contrib.auth import get_user_model
from django.db.models import Q
from guardian.shortcuts import assign_perm, get_perms
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.models import User, regex_validator
from business.models import *
from business.signals import employee_invitation_status_changed


class BaseSerializerMixin(serializers.Serializer):
    permissions = serializers.SerializerMethodField()

    def get_permissions(self, obj):
        user = self.context.get("request").user
        if user.is_authenticated:
            return list(get_perms(user, obj))
        return []


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"

    def validate(self, attrs):
        attrs = super().validate(attrs)
        lat = attrs.get("lat")
        lng = attrs.get("lng")

        errors = {}

        if lat is not None and (lat < -90 or lat > 90):
            errors["lat"] = "latitude should be between -90 and 90"

        if lng is not None and (lng < -180 or lng > 180):
            errors["lng"] = "longitude should be between -180 and 180"

        if errors:
            raise ValidationError(errors)

        return attrs


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


class BranchSerializer(serializers.ModelSerializer, BaseSerializerMixin):
    business = serializers.PrimaryKeyRelatedField(
        queryset=Business.objects.all(),
        required=True,
        allow_null=False,
    )

    # current_user_role = serializers.SerializerMethodField()

    # def get_current_user_role(self, obj):

    #     employee = Employee.objects.filter(
    #         Q(branch=obj) | Q(branch=None),
    #         user=self.context.get("request").user,
    #         business=obj.business,
    #     ).first()

    #     if not employee:
    #         return None

    #     return employee.role.id if employee.role else None

    class Meta:
        model = Branch
        fields = "__all__"


class BusinessSerializer(serializers.ModelSerializer, BaseSerializerMixin):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    address = AddressSerializer()

    class Meta:
        model = Business
        fields = "__all__"
        read_only_fields = ["is_verified", "is_active"]

    def create(self, validated_data):
        address = validated_data.pop("address")
        address = Address.objects.create(**address)
        validated_data["address"] = address
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "address" in validated_data:
            address = validated_data.pop("address")
        return super().update(instance, validated_data)


class IndustrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Industry
        exclude = []


class BusinessImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessImage
        exclude = []


class EmployeeSerializer(serializers.ModelSerializer, BaseSerializerMixin):
    class Meta:
        model = Employee
        exclude = []

    def create(self, validated_data):
        user = validated_data.pop("user")
        user = User.objects.create(**user)
        validated_data["user"] = user
        return super().create(validated_data)


class EmployeeInvitationSerializer(serializers.ModelSerializer, BaseSerializerMixin):

    def validate(self, attrs):
        attrs = super().validate(attrs)
        email = attrs.get("email")
        phone_number = attrs.get("phone_number")
        if not email and not phone_number:
            raise ValidationError("Email or phone number is required")

        if phone_number:
            if not regex_validator.regex.match(phone_number):
                raise ValidationError({"phone_number": "Invalid phone number"})

        return attrs

    class Meta:
        model = EmployeeInvitation
        exclude = []
        read_only_fields = ["status"]


class EmployeeInvitationStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=list(map(lambda x: x[0], EmployeeInvitation.STATUS_CHOICES))
    )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        status = attrs.get("status")
        if status not in list(map(lambda x: x[0], EmployeeInvitation.STATUS_CHOICES)):
            raise ValidationError({"status": "Invalid status"})
        return attrs

    def update(self, instance, validated_data):
        instance.status = validated_data.get("status")
        instance.save()
        employee_invitation_status_changed.send(
            sender=instance.__class__, instance=instance, status=instance.status
        )
        return instance

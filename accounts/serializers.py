import json
import requests
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import serializers
from django.core.mail import send_mail
from django.conf import settings
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import (
    Supplier,
    Customer,
    Business,
    Employee,
    EmployeeInvitation,
    EmployeeBusiness,
)


User = get_user_model()

email_url = settings.EMAIL_URL
notification_api_key = settings.NOTIFICATION_API_KEY


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "phone", "password")
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request", None)
        if request and request.method != "POST":
            fields.pop("password", None)
        return fields

    def create(self, validated_data):
        email = validated_data.get("email")
        phone = validated_data.get("phone")
        if email or phone:
            password = validated_data.pop("password", None)
            user = super().create(validated_data)
            if password:
                user.set_password(password)
                user.save()
            return user
        raise serializers.ValidationError("Email or phone is required.")


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist.")
        return value

    def save(self):
        request = self.context.get("request")
        user = User.objects.get(email=self.validated_data["email"])
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{request.scheme}://{request.get_host()}/accounts/password-reset-confirm/{uid}/{token}/"
        email_message = "Click the link below to reset your password:\n\n" + reset_url
        email_subject = "Password Reset"
        recipients = user.email
        payload = json.dumps(
            {
                "subject": email_subject,
                "message": email_message,
                "recipients": recipients,
            }
        )
        headers = {
            "Authorization": f"Api-Key {notification_api_key}",
            "Content-Type": "application/json",
        }
        response = requests.request("POST", email_url, headers=headers, data=payload)


class SetNewPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)
    password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError("Passwords do not match.")
        return attrs

    def save(self, user):
        user.set_password(self.validated_data["password"])
        user.save()
        return user


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError("New passwords do not match.")
        return attrs

    def save(self, user):
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "identifier"

    def validate(self, attrs):
        identifier = attrs.get("identifier")
        password = attrs.get("password", "")
        if not identifier or not password:
            raise serializers.ValidationError("Identifier and password are required.")

        user = authenticate(
            request=self.context.get("request"), username=identifier, password=password
        )
        if not user:
            print(user)
            raise serializers.ValidationError("No user with these credentials.")

        refresh = self.get_token(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "phone": user.phone,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role if hasattr(user, "role") else None,
            },
        }

        return data


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = "__all__"


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = "__all__"


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = "__all__"


class EmployeeBusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeBusiness
        fields = ("business", "role")


class EmployeeSerializer(serializers.ModelSerializer):
    # This read_only field remains available for GET responses.
    employee_businesses = EmployeeBusinessSerializer(
        source="employeebusiness_set", many=True, read_only=True
    )
    # Write-only fields for update/delete operations.
    business = serializers.PrimaryKeyRelatedField(
        queryset=Business.objects.all(), write_only=True, required=False
    )
    role = serializers.ChoiceField(
        choices=Employee.ROLE_CHOICES, write_only=True, required=False
    )

    class Meta:
        model = Employee
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "phone",
            "password",
            "created_by",
            "employee_businesses",
            "business",
            "role",
        )
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        # Remove business and role if they accidentally get passed during creation.
        validated_data.pop("business", None)
        validated_data.pop("role", None)
        employee = Employee(**validated_data)
        if password:
            employee.set_password(password)
        employee.save()
        return employee

    def update(self, instance, validated_data):
        business = validated_data.pop("business", None)
        role = validated_data.pop("role", None)
        # Update any other Employee fields.
        instance = super().update(instance, validated_data)
        if business and role:
            try:
                eb = EmployeeBusiness.objects.get(employee=instance, business=business)
                # Update the role if different.
                if eb.role != role:
                    eb.role = role
                    eb.save()
            except EmployeeBusiness.DoesNotExist:
                EmployeeBusiness.objects.create(
                    employee=instance, business=business, role=role
                )
        return instance


class EmployeeInvitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeInvitation
        fields = ["email", "first_name", "last_name", "phone", "role", "business"]

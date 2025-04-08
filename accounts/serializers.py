import json
import os
import re
from datetime import timedelta

import requests
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import serializers
from rest_framework.exceptions import NotFound
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken, Token

from accounts.utils import *

from .models import (
    Address,
    Branch,
    Business,
    Category,
    EmailChangeRequest,
    Password,
    PhoneChangeRequest,
    Role,
    RolePermission,
)

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = "__all__"

    def create(self, validated_data):
        email = validated_data.get("email")
        phone = validated_data.get("phone_number")
        if email is None or phone is None:
            raise serializers.ValidationError("Email or phone is required.")
        password = validated_data.pop("password", None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            Password.objects.create(user=user, password=user.password)
            user.save()
        return user

    def update(self, instance, validated_data):
        for field in [
            "email",
            "phone_number",
            "password",
            "is_staff",
            "is_superuser",
        ]:
            validated_data.pop(field, None)
        return super().update(instance, validated_data)


class PhoneChangeRequestSerializer(serializers.Serializer):
    new_phone = serializers.CharField(max_length=15)

    def validate_new_phone(self, value):
        phone_regex = r"^(9|7)\d{8}$"
        if not re.match(phone_regex, value):
            raise serializers.ValidationError(
                "Phone number must be entered in the format: \
                '912345678 / 712345678'. Up to 9 digits allowed."
            )
        return value

    def save(self):
        request = self.context.get("request")
        user = request.user

        expires_at = timezone.now() + timedelta(hours=1)
        PhoneChangeRequest.objects.create(
            user=user,
            new_phone=self.validated_data["new_phone"],
            expires_at=expires_at,
        )

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        confirm_url = f"""
                {request.scheme}://{request.get_host()}/accounts/phone-change-confirm/{uid}/{token}/
                """

        email_message = (
            "Click the link below to confirm your phone number change:\n\n"
            + confirm_url
        )
        email_subject = "Phone Number Change Confirmation"
        payload = json.dumps(
            {
                "subject": email_subject,
                "message": email_message,
                "recipients": user.email,
            }
        )
        notification_api_key = os.environ.get("NOTIFICATION_API_KEY")
        email_url = os.environ.get("EMAIL_URL")
        headers = {
            "Authorization": f"Api-Key {notification_api_key}",
            "Content-Type": "application/json",
        }
        requests.request("POST", email_url, headers=headers, data=payload)


class EmailChangeRequestSerializer(serializers.Serializer):
    new_email = serializers.EmailField()

    def save(self):
        request = self.context.get("request")
        user = request.user
        expires_at = timezone.now() + timedelta(hours=1)
        EmailChangeRequest.objects.create(
            user=user,
            new_email=self.validated_data["new_email"],
            expires_at=expires_at,
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        confirm_url = f"""
                {request.scheme}://{request.get_host()}/accounts/email-change-confirm/{uid}/{token}/
                """
        email_message = (
            "Click the link below to confirm\
                  your email change:\n\n"
            + confirm_url
        )
        email_subject = "Email Change Confirmation"
        payload = json.dumps(
            {
                "subject": email_subject,
                "message": email_message,
                "recipients": user.email,
            }
        )
        notification_api_key = os.environ.get("NOTIFICATION_API_KEY")
        email_url = os.environ.get("EMAIL_URL")
        headers = {
            "Authorization": f"Api-Key {notification_api_key}",
            "Content-Type": "application/json",
        }
        requests.request("POST", email_url, headers=headers, data=payload)


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

        if lng < -90 or lng > 90:
            errors["lng"] = "longitude should be between -180 and 180"

        if errors:
            raise ValidationError(errors)

        return attrs


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


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "User with this email does not exist.",
            )
        return value

    def save(self):
        request = self.context.get("request")
        user = User.objects.get(email=self.validated_data["email"])
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"""
          {request.scheme}://{request.get_host()}/accounts/password-reset-confirm/{uid}/{token}/
          """
        email_message = (
            "Click the link below to reset \
          your password:\n\n"
            + reset_url
        )
        email_subject = "Password Reset"
        recipients = user.email
        payload = json.dumps(
            {
                "subject": email_subject,
                "message": email_message,
                "recipients": recipients,
            }
        )
        notification_api_key = os.environ.get("NOTIFICATION_API_KEY")
        email_url = os.environ.get("EMAIL_URL")
        headers = {
            "Authorization": f"Api-Key {notification_api_key}",
            "Content-Type": "application/json",
        }
        requests.request("POST", email_url, headers=headers, data=payload)


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
        password = attrs.get("password", None)
        if not identifier or not password:
            raise serializers.ValidationError(
                "Identifier and password are required.",
            )

        user = authenticate(
            request=self.context.get("request"),
            username=identifier,
            password=password,
        )
        if not user:
            raise NotFound("No user with these credentials.")

        refresh = self.get_token(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "email": user.email,
                "phone_number": user.phone_number,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
                "is_superuser": user.is_superuser,
                "is_staff": user.is_staff,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            },
        }

        return data


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


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = "__all__"


class RolePermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RolePermission
        fields = "__all__"


class EmployeeInvitationSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    business_id = serializers.UUIDField()
    role_id = serializers.UUIDField()

    def save(self):
        user = User.objects.get(id=self.validated_data["user_id"])
        business = Business.objects.get(id=self.validated_data["business_id"])
        role = Role.objects.get(id=self.validated_data["role_id"])
        # Send email to user
        request = self.context.get("request")
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        invitation_url = f"""
          {request.scheme}://{request.get_host()}/accounts/employee-invitation-confirm/{business.id}/{role.id}/{uid}/{token}/
          """
        email_message = (
            f"""
            Click the link below to accept the invitation
            to join {business.name} as a {role.role_name}:\n\n
            """
            + invitation_url
        )
        email_subject = "Employee Invitation"
        recipients = user.email
        payload = json.dumps(
            {
                "subject": email_subject,
                "message": email_message,
                "recipients": recipients,
            }
        )
        notification_api_key = os.environ.get("NOTIFICATION_API_KEY")
        email_url = os.environ.get("EMAIL_URL")
        headers = {
            "Authorization": f"Api-Key {notification_api_key}",
            "Content-Type": "application/json",
        }
        requests.request("POST", email_url, headers=headers, data=payload)


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = "__all__"


# Used to specify an empty serializer used by redocs UI for schema generation
class EmptySerializer(serializers.Serializer):
    pass


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, max_length=255)

    class Meta:
        exclude = [
            "groups",
            "user_permissions",
            "is_staff",
            "is_superuser",
            "last_login",
        ]
        model = User
        read_only_fields = (
            "last_login",
            "is_active",
            "date_joined",
            "is_email_verified",
            "is_phone_verified",
        )


class UserReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = [
            "groups",
            "user_permissions",
            "is_staff",
            "is_superuser",
            "last_login",
            "password",
        ]


class LoginSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserReadSerializer(read_only=True)
    password = serializers.CharField(write_only=True)
    email = serializers.CharField(write_only=True, required=False)
    phone_number = serializers.CharField(write_only=True, required=False)
    actions = serializers.ListField(read_only=True)

    def validate(self, attrs):

        attrs = super().validate(attrs)

        user = authenticate(self.context.get("request"), **attrs)

        if not user:
            raise ValidationError(
                {
                    key: ["No user found with the given credentials"]
                    for key in attrs.keys()
                },
                400,
            )

        attrs["user"] = user

        return attrs

    def create(self, validated_data):
        user = validated_data.pop("user")

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        return {
            "user": user,
            "refresh": refresh_token,
            "access": access_token,
            "actions": get_required_user_actions(user),
        }


class RefreshLoginSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField()

    def validate(self, attrs):
        attrs = super().validate(attrs)

        try:
            refresh = RefreshToken(attrs.get("refresh"), verify=True)
            attrs["refresh"] = refresh
        except TokenError:
            raise ValidationError({"refresh": ["invalid token"]}, 400)

        return attrs

    def create(self, validated_data):
        refresh = validated_data.pop("refresh")
        access_token = str(refresh.access_token)

        refresh.set_jti()
        refresh.set_exp()
        refresh.set_iat()

        return {
            "refresh": str(refresh),
            "access": access_token,
        }


class LoginWithGoogleIdTokenSerializer(serializers.Serializer):
    id_token = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserReadSerializer(read_only=True)
    actions = serializers.ListField(read_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        userInfo = verify_google_id_token(attrs.get("id_token"))
        if not userInfo:
            raise ValidationError({"id_token": ["invalid id token"]}, 400)
        return userInfo

    def create(self, validated_data):
        email = validated_data.pop("email")
        first_name = validated_data.pop("given_name")
        last_name = validated_data.pop("family_name")
        user = User.objects.filter(email=email).first()

        if not user:

            user = User.objects.create(
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_email_verified=True,
                is_active=True,
            )
        else:
            user.is_email_verified = True

            user.save()

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        return {
            "user": user,
            "refresh": refresh_token,
            "access": access_token,
            "actions": get_required_user_actions(user),
        }


class ResetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.CharField(read_only=True, required=False)
    phone_number = serializers.CharField(read_only=True, required=False)
    detail = serializers.CharField(read_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        user = User.objects.filter(**attrs).first()

        if not user:
            raise ValidationError(
                {key: [f"no user found with given {key}"] for key in attrs.keys()}, 404
            )
        attrs["user"] = user
        return attrs

    def create(self, validated_data):
        email = validated_data.get("email")
        phone_number = validated_data.get("phone_number")
        user = validated_data.get("user")

        if email:
            # TODO handle email sending
            pass
        if phone_number:
            # TODO handle phone sending
            pass
        return {"detail": "success"}

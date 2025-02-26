import json
import os
import re
from datetime import datetime, timedelta

import requests
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Business, EmailChangeRequest, Password, PhoneChangeRequest

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
            Password.objects.create(user=user, password=password)
            user.set_password(password)
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

        expires_at = datetime.now() + timedelta(hours=1)
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
        expires_at = datetime.now() + timedelta(hours=1)
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


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = "__all__"


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
            print(user)
            raise serializers.ValidationError(
                "No user with these credentials.",
            )

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

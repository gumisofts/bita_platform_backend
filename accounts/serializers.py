import json
import os
import re
from datetime import timedelta

import requests
from django.contrib.auth import authenticate, get_user_model, password_validation
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

from accounts.models import *
from accounts.utils import *

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
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

        if lng < -180 or lng > 180:
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
    status = serializers.CharField(read_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = getattr(self, "instance", None)
        errors = {}
        print(Password.hash_password("Hello,World!"))
        print(Password.hash_password("Hello,World!"))
        password = (
            Password.objects.filter(
                password=Password.hash_password(attrs.get("new_password"))
            )
            .order_by("created_at")
            .first()
        )
        if not instance.check_password(attrs.get("old_password")):
            errors["old_password"] = ["Old password is not correct."]

        if password:
            errors["new_password"] = [
                "you cannot use one of your old passwords as new password"
            ]

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    def update(self, instance, validated_data):
        old_password = instance.password
        instance.set_password(validated_data.get("new_password"))
        instance.save()

        Password.objects.create(password=old_password)

        return {"status": "password changed successfully"}


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


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = "__all__"


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

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if "phone_number" not in attrs and "email" not in attrs:
            raise ValidationError(
                {
                    "phone_number": "either email or phone_number is required",
                    "email": "either email or phone_number is required",
                }
            )

        return attrs

    def create(self, validated_data):
        user = super().create(validated_data)
        email = validated_data.get("email")
        phone_number = validated_data.get("phone_number")

        if email:
            VerificationCode.objects.create(
                user=user,
                code="123456",
                email=email,
                # phone_number=phone_number,
                expires_at=timezone.now() + timedelta(minutes=5),
            )
        if phone_number:
            VerificationCode.objects.create(
                user=user,
                code="123456",
                # email=email,
                phone_number=phone_number,
                expires_at=timezone.now() + timedelta(minutes=5),
            )

        return user


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


class ResetPasswordRequestSerializer(serializers.ModelSerializer):
    email = serializers.CharField(write_only=True, required=False)
    phone_number = serializers.CharField(write_only=True, required=False)
    detail = serializers.CharField(read_only=True)

    class Meta:
        model = ResetPasswordRequest
        exclude = ["user", "code", "is_used"]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        user = User.objects.filter(**attrs).first()

        if not user:
            raise ValidationError(
                {key: [f"no user found with given {key}"] for key in attrs.keys()}, 404
            )
        attrs["user"] = user
        # code = generate_secure_six_digits()
        code = str(123456)  # TODO change this on production
        # TODO send the generated code
        print(code)
        attrs["code"] = make_password(code)
        return attrs

    def create(self, validated_data):
        super().create(validated_data)
        return {"detail": "success"}


class ConfirmResetPasswordRequestViewsetSerializer(serializers.Serializer):
    code = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    email = serializers.CharField(required=False, write_only=True)
    phone_number = serializers.CharField(required=False, write_only=True)

    detail = serializers.CharField(read_only=True)

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if not attrs.get("email") and not attrs.get("phone_number"):
            raise ValidationError(
                {
                    "email": ["both email and phone_number could not be empty"],
                    "phone_number": ["both email and phone_number could not be empty"],
                },
                400,
            )
        code = attrs.pop("code")
        new_password = attrs.pop("new_password")

        user = User.objects.filter(**attrs).first()

        if not user:
            raise ValidationError(
                {key: [f"no user found with the given {key}"] for key in attrs.key()},
                400,
            )

        try:
            password_validation.validate_password(new_password, user)
        except ValidationError as e:
            raise ValidationError({"password": e})

        attrs["user"] = user

        obj = (
            ResetPasswordRequest.objects.filter(**attrs)
            .order_by("created_at")
            .filter(is_used=False)
            .last()
        )

        if not obj:
            raise ValidationError(
                {"detail": "no reset request found for the given user"}, 400
            )

        if not check_password(code, obj.code):

            raise ValidationError({"code": ["invalid code"]}, 400)

        attrs["reset_request"] = obj
        attrs["new_password"] = new_password

        return attrs

    def create(self, validated_data):

        user = validated_data.pop("user")

        new_password = validated_data.pop("new_password")

        user.set_password(new_password)

        obj = validated_data.pop("reset_request")
        obj.is_used = True
        obj.save()

        return {"detail": "success"}


class ConfirmVerificationCodeSerializer(serializers.ModelSerializer):
    code = serializers.CharField(write_only=True)
    phone_number = serializers.CharField(write_only=True, required=False)
    email = serializers.CharField(write_only=True, required=False)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)
    user = UserReadSerializer(read_only=True)

    class Meta:
        model = VerificationCode
        exclude = ["is_used", "expires_at", "created_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if not "phone_number" in attrs and not "email" in attrs:
            raise ValidationError(
                {
                    "phone_number": "either phone_number or email is required",
                    "email": "either phone_number or email is required",
                },
                400,
            )
        if "phone_number" in attrs and "email" in attrs:
            raise ValidationError(
                {
                    "phone_number": "cannot include both email and phone_number",
                    "email": "cannot include both email and phone_number",
                }
            )

        code = attrs.pop("code")

        instance = (
            VerificationCode.objects.filter(is_used=False, **attrs)
            .order_by("created_at")
            .last()
        )

        if not instance or not check_password(code, instance.code):
            raise ValidationError({"code": "invalid verification code"}, 400)

        attrs["instance"] = instance

        return attrs

    def create(self, validated_data):

        instance = validated_data.get("instance")

        if "phone_number" in validated_data:

            instance.user.is_phone_verified = True
        else:

            instance.user.is_email_verified = True

        instance.user.save()
        instance.detail = "success"
        instance.is_used = True
        instance.save()

        return instance

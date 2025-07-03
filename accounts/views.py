from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
)
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from accounts.models import *
from accounts.serializers import *

User = get_user_model()


class UserViewSet(
    ListModelMixin,
    RetrieveModelMixin,
    GenericViewSet,
    UpdateModelMixin,
    CreateModelMixin,
):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_serializer(self, *args, **kwargs):
        if self.action == "me":
            return UserSerializer(*args, **kwargs)
        elif self.action == "register":
            return RegisterSerializer(*args, **kwargs)
        elif self.action == "login":
            return LoginSerializer(*args, **kwargs)
        elif self.action == "login_with_google":
            return LoginWithGoogleIdTokenSerializer(*args, **kwargs)
        elif self.action == "refresh_login":
            return RefreshLoginSerializer(*args, **kwargs)
        elif self.action == "reset_request":
            return ResetPasswordRequestSerializer(*args, **kwargs)
        elif self.action == "password_change":
            return PasswordChangeSerializer(*args, **kwargs)
        elif self.action == "reset_password_request":
            return ResetPasswordRequestSerializer(*args, **kwargs)
        elif self.action == "confirm_reset_password_request":
            return ConfirmResetPasswordRequestViewsetSerializer(*args, **kwargs)
        elif self.action == "confirm_verification_code":
            return ConfirmVerificationCodeSerializer(*args, **kwargs)

    @action(
        detail=False,
        methods=["delete"],
        permission_classes=[IsAuthenticated],
    )
    def delete(self, request, *args, **kwargs):
        instance = self.request.user
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def me(self, request):
        user = request.user
        serializer = self.get_serializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AuthViewset(GenericViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_success_headers(self, data):
        try:
            return {"Location": str(data[api_settings.URL_FIELD_NAME])}
        except (TypeError, KeyError):
            return {}

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[],
    )
    def register(self, request):
        user = request.data
        serializer = RegisterSerializer(data=user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[],
    )
    def login(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[],
        url_path="google/login",
    )
    def login_with_google(self, request):
        serializer = LoginWithGoogleIdTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[],
        serializer_class=RefreshLoginSerializer,
    )
    def refresh_login(self, request):
        serializer = RefreshLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @action(
        detail=False,
        methods=["post"],
        url_path="password/reset/request",
        permission_classes=[],
    )
    def reset_request(self, request):
        serializer = ResetPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @action(
        detail=False,
        methods=["post"],
        url_path="phone/change/request",
        permission_classes=[IsAuthenticated],
    )
    def phone_change_request(self, request):
        serializer = PhoneChangeRequestSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @action(
        detail=False,
        methods=["post"],
        url_path="phone/change/confirm",
        permission_classes=[],
    )
    def phone_change_confirm(self, request):
        serializer = PhoneChangeConfirmSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @action(
        detail=False,
        methods=["post"],
        url_path="email/change/request",
        permission_classes=[IsAuthenticated],
    )
    def email_change_request(self, request):
        serializer = EmailChangeRequestSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @action(
        detail=False,
        methods=["post"],
        url_path="email/change/confirm",
        permission_classes=[],
    )
    def email_change_confirm(self, request):
        serializer = EmailChangeConfirmSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @action(
        detail=False,
        methods=["post"],
        url_path="password/reset/confirm",
        permission_classes=[],
    )
    def confirm_reset_password_request(self, request):
        serializer = ConfirmResetPasswordRequestViewsetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @action(
        detail=False,
        methods=["post"],
        url_path="password/change",
        permission_classes=[IsAuthenticated],
    )
    def password_change(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @action(
        detail=False,
        methods=["post"],
        url_path="verifications/send",
        permission_classes=[AllowAny],
    )
    def send_verification_code(self, request):
        serializer = SendVerificationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

    @action(
        detail=False,
        methods=["post"],
        url_path="verifications/confirm",
        permission_classes=[AllowAny],
    )
    def confirm_verification_code(self, request):
        serializer = ConfirmVerificationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)


class JWTTokenVerifyView(TokenVerifyView):
    permission_classes = (AllowAny,)

    def post(self, request, *args, **kwargs):
        try:
            # Validate the token using the parent serializer
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response(
                {"detail": "Token is invalid or expired"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Decode token and fetch user data
        token = request.data.get("token")
        access_token = AccessToken(token)
        user_id = access_token.get("user_id")
        user = User.objects.get(id=user_id)
        user_data = UserSerializer(user).data
        user_data.update({"id": user_id})

        return Response(
            {"detail": "Token is valid", "user": user_data},
            status=status.HTTP_200_OK,
        )


# class ConfirmVerificationCodeViewset(CreateModelMixin, GenericViewSet):
#     serializer_class = ConfirmVerificationCodeSerializer

#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         self.perform_create(serializer)
#         headers = self.get_success_headers(serializer.data)
#         return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)


# class SendVerificationCodeViewset(CreateModelMixin, GenericViewSet):
#     serializer_class = SendVerificationCodeSerializer

#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         self.perform_create(serializer)
#         headers = self.get_success_headers(serializer.data)
#         return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)


class UserDeviceViewset(CreateModelMixin, GenericViewSet):
    serializer_class = UserDeviceSerializer

    permission_classes = []

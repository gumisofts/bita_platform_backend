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
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
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
    ListModelMixin, RetrieveModelMixin, DestroyModelMixin, GenericViewSet
):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterViewset(CreateModelMixin, GenericViewSet):
    serializer_class = RegisterSerializer


class LoginViewset(CreateModelMixin, GenericViewSet):
    serializer_class = LoginSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)


class LoginWithGoogleViewset(CreateModelMixin, GenericViewSet):
    serializer_class = LoginWithGoogleIdTokenSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)


class RefreshLoginViewset(CreateModelMixin, GenericViewSet):
    serializer_class = RefreshLoginSerializer


class ResetRequestViewset(CreateModelMixin, GenericViewSet):
    serializer_class = ResetPasswordRequestSerializer


class PasswordChangeViewset(UpdateModelMixin, GenericViewSet):
    serializer_class = PasswordChangeSerializer
    permission_classes = [IsAuthenticated]
    queryset = User.objects.filter()


class ResetPasswordRequestViewset(CreateModelMixin, GenericViewSet):
    serializer_class = ResetPasswordRequestSerializer


class ConfirmResetPasswordRequestViewset(CreateModelMixin, GenericViewSet):
    serializer_class = ConfirmResetPasswordRequestViewsetSerializer


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


class ConfirmVerificationCodeViewset(CreateModelMixin, GenericViewSet):
    serializer_class = ConfirmVerificationCodeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)


class SendVerificationCodeViewset(CreateModelMixin, GenericViewSet):
    serializer_class = SendVerificationCodeSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK, headers=headers)

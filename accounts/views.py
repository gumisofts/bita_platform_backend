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
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenVerifyView

from .models import (
    Address,
    Branch,
    Business,
    Category,
    EmailChangeRequest,
    Employee,
    PhoneChangeRequest,
    Role,
    RolePermission,
)
from .serializers import (
    AddressSerializer,
    BranchSerializer,
    BusinessSerializer,
    CategorySerializer,
    CustomTokenObtainPairSerializer,
    EmailChangeRequestSerializer,
    EmployeeInvitationSerializer,
    EmptySerializer,
    PasswordChangeSerializer,
    PasswordResetSerializer,
    PhoneChangeRequestSerializer,
    RolePermissionSerializer,
    RoleSerializer,
    SetNewPasswordSerializer,
    UserSerializer,
)

User = get_user_model()


@extend_schema(
    summary="User Management",
    tags=["Accounts"],
    description="Retrieve, create, update, or delete users.",
)
@extend_schema_view(
    list=extend_schema(
        summary="List Users",
        description="Retrieve a list of all users. (Admin only)",
    ),
    create=extend_schema(
        summary="Create User",
        description="Create a new user. (Registration endpoint)",
        examples=[
            OpenApiExample(
                "Example 1",
                value={
                    "email": "user@example.com",
                    "first_name": "string",
                    "last_name": "string",
                    "phone": "924530740",
                    "password": "password",
                },
                request_only=True,  # Ensures this is only for requests
            ),
        ],
    ),
    retrieve=extend_schema(
        summary="Retrieve User",
        description="Retrieve a single user by its ID. \
            (Admin or the user queried)",
    ),
    update=extend_schema(
        summary="Update User",
        description="Update a user completely.",
    ),
    partial_update=extend_schema(
        summary="Partial Update User",
        description="Partially update a user instance.",
    ),
    destroy=extend_schema(
        summary="Delete User",
        description="Delete a user instance.",
    ),
)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    tags=["Accounts"],
)
class PhoneChangeRequestView(generics.GenericAPIView):
    serializer_class = PhoneChangeRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Phone change request sent."}, status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Accounts"],
)
class PhoneChangeConfirmView(generics.GenericAPIView):
    serializer_class = EmptySerializer

    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Invalid link."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        phone_request = (
            PhoneChangeRequest.objects.filter(
                user=user,
                expires_at__gte=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )
        if not phone_request:
            return Response(
                {"detail": "No valid phone change request found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.phone_number = phone_request.new_phone
        user.save()
        phone_request.delete()
        return Response(
            {"detail": "Phone number has been changed."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Accounts"],
)
class EmailChangeRequestView(generics.GenericAPIView):
    serializer_class = EmailChangeRequestSerializer

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Email change confirmation link sent."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Accounts"],
)
class EmailChangeConfirmView(generics.GenericAPIView):
    serializer_class = EmptySerializer

    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Invalid link."}, status=status.HTTP_400_BAD_REQUEST
            )
        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        email_request = (
            EmailChangeRequest.objects.filter(
                user=user,
                expires_at__gte=timezone.now(),
            )
            .order_by("-created_at")
            .first()
        )
        if not email_request:
            return Response(
                {"detail": "No valid email change request found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.email = email_request.new_email
        user.save()
        email_request.delete()
        return Response(
            {"detail": "Email has been changed."}, status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Accounts"],
)
class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer


@extend_schema(
    tags=["Accounts"],
)
@extend_schema_view(
    post=extend_schema(
        summary="Password Reset",
        description="Send a password reset link to the user's email.",
    ),
)
class PasswordResetView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Password reset link sent."}, status=status.HTTP_200_OK
        )


@extend_schema(
    summary="Password Reset Confirm",
    tags=["Accounts"],
    description="Confirm the password reset by setting a new password.",
    parameters=[
        OpenApiParameter("uidb64", OpenApiTypes.STR, location="path"),
        OpenApiParameter("token", OpenApiTypes.STR, location="path"),
    ],
)
class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = SetNewPasswordSerializer

    def post(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Invalid link."}, status=status.HTTP_400_BAD_REQUEST
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user)
        return Response(
            {"detail": "Password has been reset."}, status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Accounts"],
)
@extend_schema_view(
    put=extend_schema(
        summary="Password Change",
        description="Change the user's password.",
    ),
)
class PasswordChangeView(generics.UpdateAPIView):
    serializer_class = PasswordChangeSerializer
    http_method_names = ["put"]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        user = self.get_object()
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(user)
        update_session_auth_hash(request, user)  # Keep the user logged in
        return Response(
            {"detail": "Password has been changed."}, status=status.HTTP_200_OK
        )


@extend_schema(
    tags=["Accounts"],
)
@extend_schema_view(
    post=extend_schema(
        summary="Login",
        description="Obtain a new access token by \
            exchanging username and password.",
    ),
)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(
    summary="Token verification",
    tags=["Accounts"],
    description="Verify the token and return user data.",
)
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


@extend_schema(
    tags=["Accounts"],
)
class AddressViewSet(viewsets.ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer


@extend_schema(
    tags=["Accounts"],
)
class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


@extend_schema(
    tags=["Accounts"],
)
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer


@extend_schema(
    tags=["Accounts"],
)
class RolePermissionViewSet(viewsets.ModelViewSet):
    queryset = RolePermission.objects.all()
    serializer_class = RolePermissionSerializer


@extend_schema(
    tags=["Accounts"],
)
class EmployeeInvitationView(generics.GenericAPIView):
    serializer_class = EmployeeInvitationSerializer

    def post(self, request):
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "Employee invitation sent."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    operation_id="employeeInvitationConfirm",
    summary="Confirm an employee invitation",
    tags=["Accounts"],
    parameters=[
        OpenApiParameter("business_id", OpenApiTypes.UUID, location="path"),
        OpenApiParameter("role_id", OpenApiTypes.UUID, location="path"),
        OpenApiParameter("uidb64", OpenApiTypes.STR, location="path"),
        OpenApiParameter("token", OpenApiTypes.STR, location="path"),
    ],
    responses={200: EmptySerializer},
)
class EmployeeInvitationConfirmView(generics.GenericAPIView):
    serializer_class = EmptySerializer

    def post(self, request, business_id, role_id, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            return Response(
                {"detail": "Invalid link."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            business = Business.objects.get(pk=business_id)
            role = Role.objects.get(pk=role_id)
        except (Business.DoesNotExist, Role.DoesNotExist):
            return Response(
                {"detail": "Invalid business or role."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        Employee.objects.create(user=user, business=business, role=role)
        return Response(
            {"detail": "Employee added to the business."},
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=["Accounts"],
)
class BranchViewSet(viewsets.ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer


def api_documentation(request):
    return render(request, "index.html")


# Password Change
# Invitation to Business
# Login
# Signup

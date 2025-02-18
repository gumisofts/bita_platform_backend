import json
from django.contrib.auth import get_user_model
from django.contrib.auth import update_session_auth_hash
from rest_framework import generics, status, viewsets
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenVerifyView
from .serializers import (
    PasswordResetSerializer,
    SetNewPasswordSerializer,
    PasswordChangeSerializer,
    UserSerializer,
    CustomTokenObtainPairSerializer,
    SupplierSerializer,
    CustomerSerializer,
    BusinessSerializer,
    EmployeeSerializer,
)
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework.permissions import IsAdminUser, IsAuthenticated, AllowAny
from .permissions import (
    IsOwnerOrAdmin,
    IsBusinessOwnerOrAdmin,
    EmployeeCreatePermission,
    EmployeeUpdatePermission,
    EmployeeDeletePermission,
    EmployeeRetrievePermission,
    IsNonEmployeeUser,
)
from .models import EmployeeBusiness, User, Supplier, Customer, Business, Employee
from django.shortcuts import render
from rest_framework_simplejwt.tokens import AccessToken
import requests
from django.conf import settings
from .models import EmployeeInvitation
from .serializers import (
    EmployeeInvitationSerializer,
)  # create one for invitation if needed
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiExample

User = get_user_model()


@extend_schema(
    summary="User Management",
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
        description="Retrieve a single user by its ID. (Admin or the user queried)",
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

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [IsAuthenticated, IsAdminUser]
        elif self.action in ["retrieve", "update", "partial_update", "destroy"]:
            self.permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
        return super().get_permissions()


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


@extend_schema_view(
    post=extend_schema(
        summary="Password Reset Confirm",
        description="Confirm the password reset by setting a new password.",
    ),
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


@extend_schema_view(
    post=extend_schema(
        summary="Login",
        description="Obtain a new access token by exchanging username and password.",
    ),
)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema_view(
    list=extend_schema(
        summary="List Suppliers",
        description="Retrieve a list of all suppliers. (Admin only)",
    ),
    retrieve=extend_schema(
        summary="Retrieve Supplier",
        description="Retrieve a single supplier by its ID. (Admin or the supplier queried)",
    ),
    create=extend_schema(
        summary="Create Supplier",
        description="Create a new supplier.",
    ),
    update=extend_schema(
        summary="Update Supplier",
        description="Update a supplier completely.",
    ),
    partial_update=extend_schema(
        summary="Partial Update Supplier",
        description="Partially update a supplier instance.",
    ),
    destroy=extend_schema(
        summary="Delete Supplier",
        description="Delete a supplier instance.",
    ),
)
class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]


@extend_schema_view(
    list=extend_schema(
        summary="List Customers",
        description="Retrieve a list of all customers. (Admin only)",
    ),
    retrieve=extend_schema(
        summary="Retrieve Customer",
        description="Retrieve a single customer by its ID. (Admin or the customer queried)",
    ),
    create=extend_schema(
        summary="Create Customer",
        description="Create a new customer.",
    ),
    update=extend_schema(
        summary="Update Customer",
        description="Update a customer completely.",
    ),
    partial_update=extend_schema(
        summary="Partial Update Customer",
        description="Partially update a customer instance.",
    ),
    destroy=extend_schema(
        summary="Delete Customer",
        description="Delete a customer instance.",
    ),
)
class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]


@extend_schema_view(
    list=extend_schema(
        summary="List Businesses",
        description="Retrieve a list of all businesses. (Admin only)",
    ),
    retrieve=extend_schema(
        summary="Retrieve Business",
        description="Retrieve a single business by its ID. (Admin or the business owner queried)",
    ),
    create=extend_schema(
        summary="Create Business",
        description="Create a new business.",
    ),
    update=extend_schema(
        summary="Update Business",
        description="Update a business completely.",
    ),
    partial_update=extend_schema(
        summary="Partial Update Business",
        description="Partially update a business instance.",
    ),
    destroy=extend_schema(
        summary="Delete Business",
        description="Delete a business instance.",
    ),
)
class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer

    def get_permissions(self):
        if self.action == "list":
            self.permission_classes = [IsAuthenticated, IsAdminUser]
        elif self.action == "create":
            self.permission_classes = [IsAuthenticated, IsNonEmployeeUser]
        else:
            self.permission_classes = [IsAuthenticated, IsBusinessOwnerOrAdmin]
        return super().get_permissions()


@extend_schema_view(
    list=extend_schema(
        summary="List Employees",
        description="Retrieve a list of all employees. (Admin only)",
    ),
    retrieve=extend_schema(
        summary="Retrieve Employee",
        description="Retrieve a single employee by its ID. (Admin, business owner or the employee queried)",
    ),
    update=extend_schema(
        summary="Update Employee", description="Update an employee completely."
    ),
    partial_update=extend_schema(
        summary="Partial Update Employee",
        description="Partially update an employee instance.",
    ),
    destroy=extend_schema(
        summary="Delete Employee Business Record",
        description="Delete the EmployeeBusiness record for the employee using the provided business and role.",
    ),
)
class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    http_method_names = ["get", "put", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.action in ["update", "partial_update"]:
            self.permission_classes = [IsAuthenticated, EmployeeUpdatePermission]
        elif self.action == "destroy":
            self.permission_classes = [IsAuthenticated, EmployeeDeletePermission]
        elif self.action == "retrieve":
            self.permission_classes = [IsAuthenticated, EmployeeRetrievePermission]
        else:
            self.permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
        return super().get_permissions()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        business_id = request.data.get("business")
        role = request.data.get("role")
        if business_id and role:
            try:
                eb = EmployeeBusiness.objects.get(
                    employee=instance, business_id=business_id, role=role
                )
                eb.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except EmployeeBusiness.DoesNotExist:
                return Response(
                    {"detail": "EmployeeBusiness instance not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"detail": "Business and role are required for deletion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    def update(self, request, *args, **kwargs):
        if "employee_businesses" in request.data:
            return Response(
                {
                    "detail": "Updating multiple businesses and roles directly is not allowed. Please use business and role fields."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if "employee_businesses" in request.data:
            return Response(
                {
                    "detail": "Updating multiple businesses and roles directly is not allowed. Please use business and role fields."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().partial_update(request, *args, **kwargs)


@extend_schema_view(
    post=extend_schema(
        summary="Token verification",
        description="Verify the token and return user data.",
    )
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


@extend_schema_view(
    post=extend_schema(
        summary="Employee Invitation Create",
        description="Create an invitation for an employee and send an invitation email.",
    )
)
class EmployeeInvitationCreateView(generics.CreateAPIView):
    """
    Creates an invitation for an employee and sends an invitation email.
    """

    serializer_class = EmployeeInvitationSerializer
    permission_classes = [IsAuthenticated, EmployeeCreatePermission]

    def perform_create(self, serializer):
        invitation = serializer.save(created_by=self.request.user)
        # Construct the acceptance URL. Adjust BASE_URL as appropriate.
        request = self.request
        acceptance_link = f"{request.scheme}://{request.get_host()}/employee/invite/accept/{invitation.token}/"
        # Send invitation email via NOTIFICATION_API.
        email_url = settings.EMAIL_URL
        notification_api_key = settings.NOTIFICATION_API_KEY
        payload = json.dumps(
            {
                "subject": "You're Invited to Join as an Employee",
                "message": f"Please click the following link to accept your invitation: {acceptance_link}",
                "recipients": invitation.email,
            }
        )
        headers = {
            "Authorization": f"Api-Key {notification_api_key}",
            "Content-Type": "application/json",
        }
        response = requests.request("POST", email_url, headers=headers, data=payload)


@extend_schema_view(
    post=extend_schema(
        summary="Employee Invitation Accept",
        description="Accept an invitation to become an employee immediately when the invitation link is clicked.",
    )
)
class EmployeeInvitationAcceptView(generics.GenericAPIView):
    """
    Accepts an invitation to become an employee immediately when the invitation link is clicked.
    Processes the invitation via a GET request and returns a JSON response.
    """

    permission_classes = [AllowAny]

    def post(self, request, token):
        try:
            invitation = EmployeeInvitation.objects.get(token=token, accepted=False)
        except EmployeeInvitation.DoesNotExist:
            return Response(
                {"detail": "Invalid or expired invitation token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if an employee with the invitation email already exists.
        if Employee.objects.filter(email=invitation.email).exists():
            employee = Employee.objects.get(email=invitation.email)
        else:
            # Create the employee using invitation data with a temporary password.
            employee = Employee.objects.create_user(
                email=invitation.email,
                phone=invitation.phone,
                password="password",
            )
        EmployeeBusiness.objects.create(
            employee=employee,
            business=invitation.business,
            role=invitation.role,
        )
        employee.first_name = invitation.first_name
        employee.last_name = invitation.last_name
        employee.created_by = invitation.created_by
        employee.save()

        # Mark invitation as accepted.
        invitation.accepted = True
        invitation.save()

        # Send congratulatory email via NOTIFICATION_API.
        email_url = settings.EMAIL_URL
        notification_api_key = settings.NOTIFICATION_API_KEY
        payload = json.dumps(
            {
                "subject": "Welcome Aboard!",
                "message": (
                    "Congratulations on joining our team. Your default password is 'password'. "
                    "Please change it after logging in."
                ),
                "recipients": invitation.email,
            }
        )
        headers = {
            "Authorization": f"Api-Key {notification_api_key}",
            "Content-Type": "application/json",
        }
        requests.request("POST", email_url, headers=headers, data=payload)

        serializer = EmployeeSerializer(employee)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


def api_documentation(request):
    return render(request, "index.html")

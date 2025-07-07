from uuid import UUID

from django.db.models import Q
from django.shortcuts import render
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from business.permissions import *
from business.serializers import *
from core.utils import is_valid_uuid


class BusinessViewset(ModelViewSet):
    queryset = Business.objects.filter(is_active=True)
    serializer_class = BusinessSerializer
    permission_classes = [hasBusinessPermission]

    def destroy(self, request, *args, **kwargs):
        business = self.get_object()
        business.is_active = False
        business.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        categories = self.request.query_params.get("categories")
        business_type = self.request.query_params.get("business_type")
        search = self.request.query_params.get("search")

        if search:
            queryset = queryset.filter(Q(name__icontains=search))

        if business_type:
            queryset = queryset.filter(business_type=business_type)

        queryset = queryset.filter(Q(owner=user) | Q(employees__user__in=[user]))

        if categories:
            queryset = queryset.filter(categories__id__in=categories.split(","))

        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="owner",
                type=OpenApiTypes.UUID,
                description="Filter by owner ID",
            ),
            OpenApiParameter(
                name="categories",
                type=OpenApiTypes.UUID,
                description="Filter by category IDs separated by commas",
            ),
            OpenApiParameter(
                name="business_type",
                type=OpenApiTypes.STR,
                description="Filter by business type",
            ),
            OpenApiParameter(
                name="search",
                type=str,
                description="Search by business name",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class AddressViewset(ModelViewSet):
    queryset = Address.objects.all()
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]  # TODO Temporarily simplified
    pagination_class = None

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        business_id = self.request.query_params.get("business_id")

        if business_id:
            try:
                # Convert business_id to UUID if it's a string
                if isinstance(business_id, str):
                    business_uuid = UUID(business_id)
                else:
                    business_uuid = business_id

                # First verify user has access to the business
                user_business = Business.objects.filter(
                    Q(owner=user) | Q(employees__user=user), id=business_uuid
                ).first()

                print(f"DEBUG: user_business = {user_business}")

                if not user_business:
                    print("DEBUG: No user business found, returning empty queryset")
                    return queryset.none()

                # Filter addresses that are either:
                # 1. The business's main address (through business.address)
                # 2. Used by branches of the business (through branch.address)
                filtered_queryset = queryset.filter(
                    Q(business=user_business) | Q(branches__business=user_business)
                ).distinct()

                print(f"DEBUG: filtered_queryset count = {filtered_queryset.count()}")
                return filtered_queryset

            except (ValueError, TypeError) as e:
                # Handle invalid UUID
                print(f"DEBUG: Exception = {e}")
                queryset = queryset.none()
        else:
            print("DEBUG: No business_id provided, returning empty queryset")
            queryset = queryset.none()
        return queryset


class CategoryViewset(ListModelMixin, GenericViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class BusinessRoleViewset(RetrieveModelMixin,ListModelMixin, GenericViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business_id")
        if business_id:
            queryset = queryset.filter(business=business_id)
        return queryset


class BranchViewset(ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [hasBranchPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        business_id = self.request.query_params.get("business_id")

        if business_id and is_valid_uuid(business_id):
            try:
                queryset = queryset.filter(business=business_id)
                employee = (
                    Employee.objects.filter(user=user, business=business_id)
                    .prefetch_related("branch")
                    .first()
                )
                if employee and employee.branch:
                    queryset = queryset.filter(id=employee.branch.id).distinct()
            except ValueError:
                # Handle invalid UUID
                queryset = queryset.none()
        else:
            queryset = queryset.none()

        return queryset

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class IndustryViewset(ListModelMixin, GenericViewSet):
    serializer_class = IndustrySerializer
    queryset = Industry.objects.filter(is_active=True)


class BusinessImageViewset(ListModelMixin, GenericViewSet):
    serializer_class = BusinessImageSerializer
    queryset = BusinessImage.objects.filter()
    permission_classes = []


class EmployeeViewset(ModelViewSet):
    queryset = Employee.objects.all()
    serializer_class = EmployeeSerializer
    permission_classes = [IsAuthenticated]  # TODO: Handle permissions
    lookup_field = "id"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        business_id = self.request.query_params.get("business_id")

        if business_id and is_valid_uuid(business_id):
            try:
                # Check if user has access to the business
                user_business = Business.objects.filter(
                    Q(owner=user) | Q(employees__user=user), id=business_id
                ).first()

                if user_business:
                    queryset = queryset.filter(business=business_id)
                else:
                    queryset = queryset.none()
            except ValueError:
                queryset = queryset.none()
        else:
            queryset = queryset.none()

        return queryset


class EmployeeInvitationViewset(ModelViewSet):
    serializer_class = EmployeeInvitationSerializer
    permission_classes = [EmployeeInvitationPermission]

    def get_queryset(self):
        queryset = EmployeeInvitation.objects.all()
        user = self.request.user
        business_id = self.request.query_params.get("business_id")

        if business_id and is_valid_uuid(business_id):
            try:
                # Check if user has access to the business
                user_business = Business.objects.filter(
                    Q(owner=user) | Q(employees__user=user), id=business_id
                ).first()

                if user_business:
                    queryset = queryset.filter(business=business_id)
                else:
                    queryset = queryset.none()
            except ValueError:
                queryset = queryset.none()
        else:
            queryset = queryset.none()

        return queryset

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ["mine", "update_status"]:
            permission_classes = [IsAuthenticated]
        else:
            permission_classes = [EmployeeInvitationPermission]
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        """
        Return the class to use for the serializer.
        """
        if self.action == "update_status":
            return EmployeeInvitationStatusSerializer
        return EmployeeInvitationSerializer

    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request):
        """
        List pending invitations for the current user.
        """
        user = request.user
        queryset = EmployeeInvitation.objects.filter(
            Q(phone_number=user.phone_number) | Q(email=user.email), status="pending"
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["patch"], url_path="status")
    def update_status(self, request, pk=None):
        """
        Update the status of an employee invitation.
        Only the invited user can update their invitation status.
        """
        try:
            invitation = EmployeeInvitation.objects.get(id=pk, status="pending")
        except EmployeeInvitation.DoesNotExist:
            return Response(
                {"detail": "Invitation not found or already processed"},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = request.user

        # Check if the user is the one who was invited
        if not (
            invitation.email == user.email
            or invitation.phone_number == user.phone_number
        ):
            return Response(
                {"detail": "You can only update your own invitations"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(invitation, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            employee_invitation_status_changed.send(
                sender=EmployeeInvitation,
                instance=invitation,
                status=serializer.validated_data.get("status"),
            )
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], url_path="resend")
    def resend(self, request, pk=None):
        """
        Resend an employee invitation.
        Only business owners/admins can resend invitations.
        """
        try:
            invitation = self.get_object()
        except EmployeeInvitation.DoesNotExist:
            return Response(
                {"error": "Invitation not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if invitation.status != "pending":
            return Response(
                {"error": "Can only resend pending invitations"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Trigger the signal to resend the invitation
        from business.signals import post_save

        post_save.send(sender=EmployeeInvitation, instance=invitation, created=False)

        return Response(
            {"message": "Invitation resent successfully"}, status=status.HTTP_200_OK
        )

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        """
        Get invitation statistics for a business.
        """
        business_id = request.query_params.get("business_id")

        if not business_id or not is_valid_uuid(business_id):
            return Response(
                {"error": "Valid business_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        try:
            # Check if user has access to the business
            user_business = Business.objects.filter(
                Q(owner=user) | Q(employees__user=user), id=business_id
            ).first()

            if not user_business:
                return Response(
                    {"error": "You don't have access to this business"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Get invitation statistics
            invitations = EmployeeInvitation.objects.filter(business=business_id)
            stats = {
                "total": invitations.count(),
                "pending": invitations.filter(status="pending").count(),
                "accepted": invitations.filter(status="accepted").count(),
                "rejected": invitations.filter(status="rejected").count(),
                "expired": invitations.filter(status="expired").count(),
                "revoked": invitations.filter(status="revoked").count(),
            }

            return Response(stats)

        except ValueError:
            return Response(
                {"error": "Invalid business_id"}, status=status.HTTP_400_BAD_REQUEST
            )

    def create(self, request, *args, **kwargs):
        """
        Create a new employee invitation.
        """
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Additional validation
            business_id = serializer.validated_data.get("business")
            if business_id:
                user = request.user
                # Check if user has permission to invite to this business
                user_business = Business.objects.filter(
                    Q(owner=user) | Q(employees__user=user), id=business_id.id
                ).first()

                if not user_business:
                    return Response(
                        {
                            "error": "You don't have permission to invite to this business"
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )

            # Check for duplicate invitations
            email = serializer.validated_data.get("email")
            phone_number = serializer.validated_data.get("phone_number")
            business = serializer.validated_data.get("business")

            existing_invitation = EmployeeInvitation.objects.filter(
                Q(email=email) | Q(phone_number=phone_number),
                business=business,
                status="pending",
            ).first()

            if existing_invitation:
                return Response(
                    {"error": "A pending invitation already exists for this user"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        """
        Revoke an employee invitation.
        """
        try:
            invitation = self.get_object()
            if invitation.status != "pending":
                return Response(
                    {"error": "Can only revoke pending invitations"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Instead of deleting, mark as revoked
            invitation.status = "revoked"
            invitation.save()

            return Response(
                {"message": "Invitation revoked successfully"},
                status=status.HTTP_200_OK,
            )
        except EmployeeInvitation.DoesNotExist:
            return Response(
                {"error": "Invitation not found"}, status=status.HTTP_404_NOT_FOUND
            )

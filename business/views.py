from django.shortcuts import render
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from business.permissions import *
from business.serializers import *


class BusinessViewset(ModelViewSet):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer
    permission_classes = [hasBusinessPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        categories = self.request.query_params.get("categories")
        business_type = self.request.query_params.get("business_type")
        search = self.request.query_params.get("search")

        if search:
            queryset = queryset.filter(name__icontains=search)
        if business_type:
            queryset = queryset.filter(business_type=business_type)

        queryset = queryset.filter(Q(owner=user) | Q(employees__user__in=[user]))

        if categories:
            queryset = queryset.filter(
                categories__id__in=categories.split(",")
            ).distinct()

        return queryset

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
    permission_classes = [BusinessAddressPermission]

    def get_queryset(self):
        queryset = super().get_queryset()
        business_id = self.request.query_params.get("business_id")
        if business_id:
            queryset = queryset.filter(business=business_id)
        else:
            queryset = []
        return queryset


class CategoryViewset(ListModelMixin, GenericViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class RoleViewset(RetrieveModelMixin, ListModelMixin, GenericViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]


class BusinessRoleViewset(ListModelMixin, GenericViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
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

        if business_id:
            queryset = queryset.filter(business=business_id)
            employee = (
                Employee.objects.filter(user=user, business=business_id)
                .prefetch_related("branch")
                .first()
            )
            print(employee, employee.branch)
            if employee.branch:
                queryset = queryset.filter(id=employee.branch.id).distinct()

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
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        business_id = self.request.query_params.get("business_id")


class EmployeeInvitationViewset(CreateModelMixin, DestroyModelMixin, GenericViewSet):
    serializer_class = EmployeeInvitationSerializer
    permission_classes = [EmployeeInvitationPermission]


class InvitationViewset(ListModelMixin, GenericViewSet):
    serializer_class = EmployeeInvitationSerializer
    permission_classes = [IsAuthenticated]
    queryset = EmployeeInvitation.objects.filter(status="pending")

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        return queryset.filter(Q(phone_number=user.phone_number) | Q(email=user.email))


class EmployeeInvitationStatusViewset(UpdateModelMixin, GenericViewSet):
    serializer_class = EmployeeInvitationStatusSerializer
    permission_classes = [IsAuthenticated]
    queryset = EmployeeInvitation.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        queryset = queryset.filter(
            Q(email=user.email) | Q(phone_number=user.phone_number), status="pending"
        )

        return queryset

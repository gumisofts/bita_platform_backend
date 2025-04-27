from django.shortcuts import render
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from business.serializers import *


class BusinessViewset(ModelViewSet):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.query_params.get("user")
        categories = self.request.query_params.get("categories")
        business_type = self.request.query_params.get("business_type")
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(name__icontains=search)
        if business_type:
            queryset = queryset.filter(business_type=business_type)

        if user:
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
    permission_classes = [IsAuthenticated]


class CategoryViewset(ListModelMixin, GenericViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class RoleViewset(RetrieveModelMixin, GenericViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]


class BranchViewset(ModelViewSet):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated]


class IndustryViewset(ListModelMixin, GenericViewSet):
    serializer_class = IndustrySerializer
    queryset = Industry.objects.filter(is_active=True)


class BusinessImageViewset(ListModelMixin, GenericViewSet):
    serializer_class = BusinessImageSerializer
    queryset = BusinessImage.objects.filter()

from django.shortcuts import render
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from business.serializers import *


class BusinessViewset(ModelViewSet):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer


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

from django.contrib.postgres.search import TrigramSimilarity
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from .models import *
from .serializers import *


class ItemViewset(ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer

    def get_queryset(self):
        queryset = Item.objects.all()
        category_id = self.request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        business_id = self.request.query_params.get("business_id")
        if business_id:
            queryset = queryset.filter(business_id=business_id)
        returnable = self.request.query_params.get("returnable")
        if returnable and returnable.lower() == "true":
            queryset = queryset.filter(is_returnable=True)
        elif returnable and returnable.lower() == "false":
            queryset = queryset.filter(is_returnable=False)
        online = self.request.query_params.get("online")
        if online and online.lower() == "true":
            queryset = queryset.filter(make_online_available=True)
        elif online and online.lower() == "false":
            queryset = queryset.filter(make_online_available=False)
        search_term = self.request.query_params.get("search")
        if search_term:
            pass
            # TODO(Abeni)

        return queryset


class SupplyViewset(ListModelMixin, CreateModelMixin, GenericViewSet):
    serializer_class = SupplySerializer
    permission_classes = [IsAuthenticated]
    queryset = Supply.objects.all()

    def get_queryset(self):
        queryset = self.queryset
        business_id = self.request.query_params.get("business_id")
        if business_id:
            queryset = queryset.filter(branch__business=business_id)
        return queryset


class SupplyItemViewset(CreateModelMixin, GenericViewSet):
    serializer_class = SuppliedItemSerializer
    permission_classes = [IsAuthenticated]
    queryset = SuppliedItem.objects.all()

    def get_queryset(self):
        queryset = self.queryset
        supply_id = self.request.query_params.get("supply_id")
        if supply_id:
            queryset = queryset.filter(supply=supply_id)
        return queryset


class PricingViewset(ModelViewSet):
    queryset = Pricing.objects.all()
    serializer_class = PricingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        variant_id = self.request.query_params.get("variant_id")
        if variant_id:
            queryset = queryset.filter(item_variant=variant_id)
        return queryset


class GroupViewset(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        item_id = self.request.query_params.get("item_id")
        if item_id:
            queryset = queryset.filter(item=item_id)
        return queryset


class ItemVariantViewset(ModelViewSet):
    queryset = ItemVariant.objects.all()
    serializer_class = ItemVariantSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset
        item_id = self.request.query_params.get("item_id")
        if item_id:
            queryset = queryset.filter(item=item_id)
        return queryset

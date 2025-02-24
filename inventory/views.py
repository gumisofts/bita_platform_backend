from django.shortcuts import render
from django.conf import settings
from django.db.models.aggregates import Count
from django.contrib.postgres.search import TrigramSimilarity
from rest_framework.viewsets import ModelViewSet, GenericViewSet
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from .models import (
    Category,
    Item,
    Location,
    Supply,
    Store,
    StockMovement,
    ReturnRecall,
    ItemImage,
    SupplyReservation,
)
from .serializers import (
    CategorySerializer,
    ItemSerializer,
    SupplySerializer,
    StoreSerializer,
    LocationSerializer,
    StockMovementSerializer,
    ReturnRecallSerializer,
    ItemImageSerializer,
    SupplyReservationSerializer,
)

# Create your views here.


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.annotate(items_count=Count("items")).all()
    serializer_class = CategorySerializer


class ItemViewSet(ModelViewSet):
    serializer_class = ItemSerializer

    @extend_schema(parameters=settings.ITEM_LIST_QUERY_PARAMETERS)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Item.objects.all()
        category_id = self.request.query_params.get("category_id")
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        manufacturer_id = self.request.query_params.get("manufacturer_id")
        if manufacturer_id:
            queryset = queryset.filter(manufacturer_id=manufacturer_id)

        visible = self.request.query_params.get("visible")
        if visible is not None:
            queryset = queryset.filter(isvisible=visible.lower() == "true")

        returnable = self.request.query_params.get("returnable")
        if returnable is not None:
            queryset = queryset.filter(is_returnable=returnable.lower() == "true")

        search_term = self.request.query_params.get("search")
        if search_term:
            queryset = (
                queryset.annotate(
                    similarity=TrigramSimilarity("name", search_term) * 2
                    + TrigramSimilarity("description", search_term)
                )
                .filter(similarity__gt=0.1)
                .order_by("-similarity")
            )

        return queryset


class SupplyViewSet(ModelViewSet):
    queryset = Supply.objects.all()
    serializer_class = SupplySerializer


class StoreViewSet(ModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer


class LocationViewSet(ModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer


class StockMovementViewSet(ModelViewSet):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer


class ItemImageViewSet(ModelViewSet):
    queryset = ItemImage.objects.all()
    serializer_class = ItemImageSerializer


class SupplyReservationViewSet(ModelViewSet):
    queryset = SupplyReservation.objects.all()
    serializer_class = SupplyReservationSerializer

    @extend_schema(parameters=settings.SUPPLY_RESERVATION_LIST_QUERY_PARAMETERS)
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset

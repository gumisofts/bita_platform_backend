from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import Avg, Case, CharField, Count, F, Q, Value, When
from django.shortcuts import render
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from business.models import Business, Category, Industry
from inventories.models import Item, ItemVariant, Property

from .serializers import (
    MarketplaceCategoryTreeSerializer,
    MarketplaceIndustrySerializer,
    MarketplaceItemVariantListSerializer,
    MarketplaceItemVariantSerializer,
    MarketplaceSearchSerializer,
)


class MarketplaceProductViewSet(ReadOnlyModelViewSet):
    """
    Comprehensive marketplace product endpoints with advanced filtering and search
    Focus on ItemVariant as the main marketplace product entity
    """

    queryset = (
        ItemVariant.objects.select_related("item", "item__business")
        .prefetch_related(
            "item__categories", "properties", "pricings", "item__itemimage_set"
        )
        .filter() # TODO: add filters
    )

    permission_classes = [AllowAny]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name", "item__name", "item__description", "sku", "batch_number"]
    ordering_fields = ["created_at", "selling_price", "quantity", "name"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return MarketplaceItemVariantListSerializer
        return MarketplaceItemVariantSerializer

    def get_queryset(self):
        queryset = self.queryset

        # Basic filtering parameters
        categories = self.request.query_params.getlist("categories")
        industries = self.request.query_params.getlist("industries")
        businesses = self.request.query_params.getlist("businesses")
        business_types = self.request.query_params.getlist("business_types")

        # Price filtering
        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")

        # Stock filtering
        in_stock_only = (
            self.request.query_params.get("in_stock_only", "true").lower() == "true"
        )
        min_quantity = self.request.query_params.get("min_quantity")

        # Date filtering
        expire_date_from = self.request.query_params.get("expire_date_from")
        expire_date_to = self.request.query_params.get("expire_date_to")

        # Business verification
        verified_only = (
            self.request.query_params.get("verified_only", "false").lower() == "true"
        )

        # Property filtering
        properties = self.request.query_params.get(
            "properties"
        )  # Format: "color:red,size:large"

        # Advanced search
        advanced_search = self.request.query_params.get("q")

        # Apply filters
        if categories:
            queryset = queryset.filter(item__categories__id__in=categories)

        if industries:
            queryset = queryset.filter(item__categories__industry__id__in=industries)

        if businesses:
            queryset = queryset.filter(item__business__id__in=businesses)

        if business_types:
            queryset = queryset.filter(item__business__business_type__in=business_types)

        if min_price:
            queryset = queryset.filter(selling_price__gte=min_price)

        if max_price:
            queryset = queryset.filter(selling_price__lte=max_price)

        if in_stock_only:
            queryset = queryset.filter(quantity__gt=0)

        if min_quantity:
            queryset = queryset.filter(quantity__gte=min_quantity)

        if expire_date_from:
            queryset = queryset.filter(
                Q(expire_date__gte=expire_date_from) | Q(expire_date__isnull=True)
            )

        if expire_date_to:
            queryset = queryset.filter(
                Q(expire_date__lte=expire_date_to) | Q(expire_date__isnull=True)
            )

        if verified_only:
            queryset = queryset.filter(item__business__is_verified=True)

        # Property-based filtering
        if properties:
            property_filters = properties.split(",")
            for prop_filter in property_filters:
                if ":" in prop_filter:
                    prop_name, prop_value = prop_filter.split(":", 1)
                    queryset = queryset.filter(
                        properties__name__iexact=prop_name.strip(),
                        properties__value__icontains=prop_value.strip(),
                    )

        # Advanced search using PostgreSQL full-text search
        if advanced_search:
            search_vector = (
                SearchVector("name", weight="A")
                + SearchVector("item__name", weight="A")
                + SearchVector("item__description", weight="B")
                + SearchVector("sku", weight="C")
                + SearchVector("batch_number", weight="C")
                + SearchVector("properties__value", weight="D")
                + SearchVector("properties__name", weight="D")
            )
            search_query = SearchQuery(advanced_search)
            queryset = (
                queryset.annotate(
                    search=search_vector, rank=SearchRank(search_vector, search_query)
                )
                .filter(search=search_query)
                .order_by("-rank", "-created_at")
            )

        return queryset.distinct()

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="categories",
                type={"type": "array", "items": {"type": "string"}},
                description="Filter by category IDs",
            ),
            OpenApiParameter(
                name="industries",
                type={"type": "array", "items": {"type": "string"}},
                description="Filter by industry IDs",
            ),
            OpenApiParameter(
                name="businesses",
                type={"type": "array", "items": {"type": "string"}},
                description="Filter by business IDs",
            ),
            OpenApiParameter(
                name="business_types",
                type={"type": "array", "items": {"type": "string"}},
                description="Filter by business types",
            ),
            OpenApiParameter(
                name="min_price",
                type=OpenApiTypes.DECIMAL,
                description="Minimum price filter",
            ),
            OpenApiParameter(
                name="max_price",
                type=OpenApiTypes.DECIMAL,
                description="Maximum price filter",
            ),
            OpenApiParameter(
                name="in_stock_only",
                type=OpenApiTypes.BOOL,
                description="Show only in-stock items",
            ),
            OpenApiParameter(
                name="min_quantity",
                type=OpenApiTypes.INT,
                description="Minimum quantity filter",
            ),
            OpenApiParameter(
                name="verified_only",
                type=OpenApiTypes.BOOL,
                description="Show only verified businesses",
            ),
            OpenApiParameter(
                name="properties",
                type=OpenApiTypes.STR,
                description="Filter by properties (format: name:value,name2:value2)",
            ),
            OpenApiParameter(
                name="q", type=OpenApiTypes.STR, description="Advanced search query"
            ),
            OpenApiParameter(
                name="expire_date_from",
                type=OpenApiTypes.DATE,
                description="Filter by expiry date from",
            ),
            OpenApiParameter(
                name="expire_date_to",
                type=OpenApiTypes.DATE,
                description="Filter by expiry date to",
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        List marketplace products with comprehensive filtering options
        """
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def featured(self, request):
        """Get featured products (high-rated, recently added, or promotional)"""
        queryset = (
            self.get_queryset()
            .filter(item__business__is_verified=True, quantity__gt=0)
            .order_by("-created_at")[:20]
        )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def trending(self, request):
        """Get trending products based on recent activity"""
        # For now, return recently added products with good stock
        queryset = (
            self.get_queryset().filter(quantity__gt=10).order_by("-created_at")[:15]
        )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        """Get products with low stock (for businesses to manage inventory)"""
        queryset = (
            self.get_queryset()
            .filter(quantity__lte=F("notify_below"), quantity__gt=0)
            .order_by("quantity")
        )

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def similar(self, request, pk=None):
        """Get similar products based on category and properties"""
        product = self.get_object()

        # Find products in same categories
        similar_queryset = (
            self.get_queryset()
            .filter(item__categories__in=product.item.categories.all())
            .exclude(id=product.id)
        )

        # Also find products with similar properties
        product_properties = product.properties.values_list("name", flat=True)
        if product_properties:
            similar_queryset = similar_queryset.filter(
                properties__name__in=product_properties
            )

        similar_products = similar_queryset.distinct()[:10]
        serializer = self.get_serializer(similar_products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def advanced_search(self, request):
        """Advanced search with multiple criteria"""
        serializer = MarketplaceSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        queryset = self.get_queryset()

        # Apply search criteria
        if data.get("query"):
            search_vector = SearchVector(
                "name", "item__name", "item__description", "sku"
            )
            search_query = SearchQuery(data["query"])
            queryset = (
                queryset.annotate(
                    search=search_vector, rank=SearchRank(search_vector, search_query)
                )
                .filter(search=search_query)
                .order_by("-rank")
            )

        if data.get("categories"):
            queryset = queryset.filter(item__categories__id__in=data["categories"])

        if data.get("business_types"):
            queryset = queryset.filter(
                item__business__business_type__in=data["business_types"]
            )

        if data.get("min_price"):
            queryset = queryset.filter(selling_price__gte=data["min_price"])

        if data.get("max_price"):
            queryset = queryset.filter(selling_price__lte=data["max_price"])

        if data.get("in_stock_only"):
            queryset = queryset.filter(quantity__gt=0)

        if data.get("verified_businesses_only"):
            queryset = queryset.filter(item__business__is_verified=True)

        # Apply sorting
        queryset = queryset.order_by(data.get("sort_by", "-created_at"))

        # Paginate results
        page = self.paginate_queryset(queryset.distinct())
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset.distinct(), many=True)
        return Response(serializer.data)


class MarketplaceCategoryViewSet(ReadOnlyModelViewSet):
    """
    Category management for marketplace with product counts and filtering
    """

    queryset = Category.objects.filter(is_active=True).select_related("industry")
    serializer_class = MarketplaceCategoryTreeSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "industry__name"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = self.queryset
        industry = self.request.query_params.get("industry")
        has_products = (
            self.request.query_params.get("has_products", "false").lower() == "true"
        )

        if industry:
            queryset = queryset.filter(industry_id=industry)

        if has_products:
            queryset = queryset.filter(
                items__variants__is_visible_online=True, items__variants__quantity__gt=0
            ).distinct()

        return queryset

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Get categories organized by industry"""
        industries = (
            Industry.objects.filter(is_active=True, category__is_active=True)
            .prefetch_related("category_set")
            .distinct()
        )

        serializer = MarketplaceIndustrySerializer(industries, many=True)
        return Response(serializer.data)


class MarketplaceBusinessViewSet(ReadOnlyModelViewSet):
    """
    Business information for marketplace
    """

    queryset = (
        Business.objects.filter(is_active=True)
        .select_related("address")
        .prefetch_related("categories")
    )

    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = self.queryset
        business_type = self.request.query_params.get("business_type")
        categories = self.request.query_params.getlist("categories")
        verified_only = (
            self.request.query_params.get("verified_only", "false").lower() == "true"
        )

        if business_type:
            queryset = queryset.filter(business_type=business_type)

        if categories:
            queryset = queryset.filter(categories__id__in=categories)

        if verified_only:
            queryset = queryset.filter(is_verified=True)

        return queryset.distinct()

    @action(detail=True, methods=["get"])
    def products(self, request, pk=None):
        """Get products for a specific business"""
        business = self.get_object()

        products = (
            ItemVariant.objects.filter(item__business=business, is_visible_online=True)
            .select_related("item")
            .prefetch_related("properties")
        )

        # Apply additional filtering
        categories = request.query_params.getlist("categories")
        if categories:
            products = products.filter(item__categories__id__in=categories)

        in_stock_only = (
            request.query_params.get("in_stock_only", "true").lower() == "true"
        )
        if in_stock_only:
            products = products.filter(quantity__gt=0)

        page = self.paginate_queryset(products.distinct())
        if page is not None:
            serializer = MarketplaceItemVariantListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MarketplaceItemVariantListSerializer(
            products.distinct(), many=True
        )
        return Response(serializer.data)


class MarketplaceStatsViewSet(GenericViewSet):
    """
    Marketplace statistics and analytics
    """

    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def overview(self, request):
        """Get marketplace overview statistics"""
        stats = {
            "total_products": ItemVariant.objects.filter(
                is_visible_online=True, item__business__is_active=True
            ).count(),
            "total_businesses": Business.objects.filter(is_active=True).count(),
            "total_categories": Category.objects.filter(is_active=True).count(),
            "products_in_stock": ItemVariant.objects.filter(
                is_visible_online=True, quantity__gt=0, item__business__is_active=True
            ).count(),
            "verified_businesses": Business.objects.filter(
                is_active=True, is_verified=True
            ).count(),
        }

        return Response(stats)

    @action(detail=False, methods=["get"])
    def categories_stats(self, request):
        """Get statistics by category"""
        categories = (
            Category.objects.filter(is_active=True)
            .annotate(
                product_count=Count(
                    "items__variants",
                    filter=Q(
                        items__variants__is_visible_online=True,
                        items__variants__quantity__gt=0,
                    ),
                ),
                business_count=Count(
                    "businesses", filter=Q(businesses__is_active=True)
                ),
            )
            .order_by("-product_count")
        )

        serializer = MarketplaceCategoryTreeSerializer(categories, many=True)
        return Response(serializer.data)

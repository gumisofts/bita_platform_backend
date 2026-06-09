from django.contrib.contenttypes.models import ContentType
from django.db.models import Avg, Count, F, Q
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from business.models import Business, Category, Industry
from inventories.models import Item, ItemVariant, Property

from .models import Review
from .serializers import (
    MarketplaceBusinessListSerializer,
    MarketplaceBusinessSerializer,
    MarketplaceCategoryTreeSerializer,
    MarketplaceIndustrySerializer,
    MarketplaceItemVariantListSerializer,
    MarketplaceItemVariantSerializer,
    MarketplaceOrderCreateSerializer,
    MarketplaceSearchSerializer,
    ReviewListSerializer,
    ReviewSerializer,
)


class MarketplaceProductViewSet(ReadOnlyModelViewSet):
    """
    Marketplace product endpoints — public, read-only.
    Products are ItemVariants that are visible online and belong to active businesses.
    """

    queryset = (
        ItemVariant.objects.select_related("item", "item__business", "item__business__address", "item__business__background_image")
        .prefetch_related(
            "item__categories",
            "properties",
            "pricings",
            "item__itemimage_set",
            "item__itemvideo_set",
        )
        .filter(
            item__is_visible_online=True,
            item__is_active=True,
            item__business__is_active=True,
        )
    )

    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "item__name", "item__description", "sku"]
    ordering_fields = ["created_at", "selling_price", "quantity", "name"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return MarketplaceItemVariantListSerializer
        return MarketplaceItemVariantSerializer

    def get_queryset(self):
        queryset = self.queryset

        categories = self.request.query_params.getlist("categories")
        industries = self.request.query_params.getlist("industries")
        businesses = self.request.query_params.getlist("businesses")
        business_types = self.request.query_params.getlist("business_types")

        min_price = self.request.query_params.get("min_price")
        max_price = self.request.query_params.get("max_price")

        in_stock_only = self.request.query_params.get("in_stock_only", "true").lower() == "true"
        min_quantity = self.request.query_params.get("min_quantity")

        expire_date_from = self.request.query_params.get("expire_date_from")
        expire_date_to = self.request.query_params.get("expire_date_to")

        verified_only = self.request.query_params.get("verified_only", "false").lower() == "true"

        properties = self.request.query_params.get("properties")
        advanced_search = self.request.query_params.get("q")

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
                Q(supplied_items__expire_date__gte=expire_date_from) | Q(supplied_items__expire_date__isnull=True)
            )
        if expire_date_to:
            queryset = queryset.filter(
                Q(supplied_items__expire_date__lte=expire_date_to) | Q(supplied_items__expire_date__isnull=True)
            )
        if verified_only:
            queryset = queryset.filter(item__business__is_verified=True)
        if properties:
            for prop_filter in properties.split(","):
                if ":" in prop_filter:
                    prop_name, prop_value = prop_filter.split(":", 1)
                    queryset = queryset.filter(
                        properties__name__iexact=prop_name.strip(),
                        properties__value__icontains=prop_value.strip(),
                    )
        if advanced_search:
            queryset = queryset.filter(
                Q(name__icontains=advanced_search)
                | Q(item__name__icontains=advanced_search)
                | Q(item__description__icontains=advanced_search)
                | Q(sku__icontains=advanced_search)
                | Q(properties__value__icontains=advanced_search)
            )

        return queryset.distinct()

    @action(detail=False, methods=["get"])
    def featured(self, request):
        """Get featured products: verified businesses, in stock, most recently added."""
        queryset = (
            self.get_queryset()
            .filter(item__business__is_verified=True, quantity__gt=0)
            .order_by("-created_at")[:20]
        )
        serializer = MarketplaceItemVariantListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def trending(self, request):
        """Get trending products based on recent activity."""
        queryset = self.get_queryset().filter(quantity__gt=10).order_by("-created_at")[:15]
        serializer = MarketplaceItemVariantListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def similar(self, request, pk=None):
        """Get similar products in the same category."""
        product = self.get_object()
        similar_qs = (
            self.get_queryset()
            .filter(item__categories__in=product.item.categories.all())
            .exclude(id=product.id)
            .distinct()[:10]
        )
        serializer = MarketplaceItemVariantListSerializer(similar_qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def reviews(self, request, pk=None):
        """Get reviews for a specific product variant."""
        product = self.get_object()
        ct = ContentType.objects.get_for_model(ItemVariant)
        reviews = Review.objects.filter(content_type=ct, object_id=product.id).select_related("reviewer")
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ReviewListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReviewListSerializer(reviews, many=True)
        return Response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter("categories", type={"type": "array", "items": {"type": "string"}}),
            OpenApiParameter("industries", type={"type": "array", "items": {"type": "string"}}),
            OpenApiParameter("businesses", type={"type": "array", "items": {"type": "string"}}),
            OpenApiParameter("business_types", type={"type": "array", "items": {"type": "string"}}),
            OpenApiParameter("min_price", type=OpenApiTypes.DECIMAL),
            OpenApiParameter("max_price", type=OpenApiTypes.DECIMAL),
            OpenApiParameter("in_stock_only", type=OpenApiTypes.BOOL),
            OpenApiParameter("min_quantity", type=OpenApiTypes.INT),
            OpenApiParameter("verified_only", type=OpenApiTypes.BOOL),
            OpenApiParameter("properties", type=OpenApiTypes.STR, description="Format: name:value,name2:value2"),
            OpenApiParameter("q", type=OpenApiTypes.STR, description="Full-text search query"),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=["post"])
    def advanced_search(self, request):
        """Advanced search with multiple criteria in request body."""
        serializer = MarketplaceSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        queryset = self.get_queryset()

        if data.get("query"):
            queryset = queryset.filter(
                Q(name__icontains=data["query"])
                | Q(item__name__icontains=data["query"])
                | Q(item__description__icontains=data["query"])
            )
        if data.get("categories"):
            queryset = queryset.filter(item__categories__id__in=data["categories"])
        if data.get("business_types"):
            queryset = queryset.filter(item__business__business_type__in=data["business_types"])
        if data.get("min_price"):
            queryset = queryset.filter(selling_price__gte=data["min_price"])
        if data.get("max_price"):
            queryset = queryset.filter(selling_price__lte=data["max_price"])
        if data.get("in_stock_only"):
            queryset = queryset.filter(quantity__gt=0)
        if data.get("verified_businesses_only"):
            queryset = queryset.filter(item__business__is_verified=True)

        queryset = queryset.order_by(data.get("sort_by", "-created_at")).distinct()
        page = self.paginate_queryset(queryset)
        if page is not None:
            s = MarketplaceItemVariantListSerializer(page, many=True)
            return self.get_paginated_response(s.data)
        s = MarketplaceItemVariantListSerializer(queryset, many=True)
        return Response(s.data)


class MarketplaceCategoryViewSet(ReadOnlyModelViewSet):
    queryset = Category.objects.filter(is_active=True).select_related("industry")
    serializer_class = MarketplaceCategoryTreeSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "industry__name"]
    ordering = ["name"]

    def get_queryset(self):
        queryset = self.queryset
        industry = self.request.query_params.get("industry")
        has_products = self.request.query_params.get("has_products", "false").lower() == "true"
        if industry:
            queryset = queryset.filter(industry_id=industry)
        if has_products:
            queryset = queryset.filter(
                items__variants__quantity__gt=0,
                items__is_visible_online=True,
            ).distinct()
        return queryset

    @action(detail=False, methods=["get"])
    def tree(self, request):
        """Get categories organised by industry."""
        industries = (
            Industry.objects.filter(is_active=True, category__is_active=True)
            .prefetch_related("category_set")
            .distinct()
        )
        serializer = MarketplaceIndustrySerializer(industries, many=True)
        return Response(serializer.data)


class MarketplaceBusinessViewSet(ReadOnlyModelViewSet):
    queryset = (
        Business.objects.filter(is_active=True)
        .select_related("address", "background_image")
        .prefetch_related("categories")
    )
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return MarketplaceBusinessListSerializer
        return MarketplaceBusinessSerializer

    def get_queryset(self):
        queryset = self.queryset
        business_type = self.request.query_params.get("business_type")
        categories = self.request.query_params.getlist("categories")
        verified_only = self.request.query_params.get("verified_only", "false").lower() == "true"
        if business_type:
            queryset = queryset.filter(business_type=business_type)
        if categories:
            queryset = queryset.filter(categories__id__in=categories)
        if verified_only:
            queryset = queryset.filter(is_verified=True)
        return queryset.distinct()

    @action(detail=True, methods=["get"])
    def products(self, request, pk=None):
        """Get all visible products for a specific business."""
        business = self.get_object()
        products = (
            ItemVariant.objects.filter(
                item__business=business,
                item__is_visible_online=True,
                item__is_active=True,
            )
            .select_related("item")
            .prefetch_related("properties", "pricings", "item__categories", "item__itemimage_set")
        )
        categories = request.query_params.getlist("categories")
        if categories:
            products = products.filter(item__categories__id__in=categories)
        in_stock_only = request.query_params.get("in_stock_only", "true").lower() == "true"
        if in_stock_only:
            products = products.filter(quantity__gt=0)

        page = self.paginate_queryset(products.distinct())
        if page is not None:
            serializer = MarketplaceItemVariantListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = MarketplaceItemVariantListSerializer(products.distinct(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def reviews(self, request, pk=None):
        """Get reviews for a specific business."""
        business = self.get_object()
        ct = ContentType.objects.get_for_model(Business)
        reviews = Review.objects.filter(content_type=ct, object_id=business.id).select_related("reviewer")
        page = self.paginate_queryset(reviews)
        if page is not None:
            serializer = ReviewListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = ReviewListSerializer(reviews, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[AllowAny])
    def place_order(self, request, pk=None):
        """
        Place a marketplace order with the business.
        Authenticated users get verified_purchase; guests just need name+email.
        Creates a CRM Customer and a pending Order record in the seller's system.
        """
        business = self.get_object()
        if not business.branches.exists():
            return Response(
                {"detail": "This business cannot accept online orders at the moment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = MarketplaceOrderCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order = serializer.create_order(business)

        return Response(
            {
                "detail": "Your order has been submitted successfully.",
                "order_id": str(order.id),
                "status": order.status,
                "total_payable": str(order.total_payable),
            },
            status=status.HTTP_201_CREATED,
        )


class MarketplaceStatsViewSet(GenericViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def overview(self, request):
        stats = {
            "total_products": ItemVariant.objects.filter(
                item__is_visible_online=True,
                item__is_active=True,
                item__business__is_active=True,
            ).count(),
            "total_businesses": Business.objects.filter(is_active=True).count(),
            "total_categories": Category.objects.filter(is_active=True).count(),
            "products_in_stock": ItemVariant.objects.filter(
                item__is_visible_online=True,
                item__is_active=True,
                item__business__is_active=True,
                quantity__gt=0,
            ).count(),
            "verified_businesses": Business.objects.filter(is_active=True, is_verified=True).count(),
        }
        return Response(stats)

    @action(detail=False, methods=["get"])
    def categories_stats(self, request):
        categories = (
            Category.objects.filter(is_active=True)
            .annotate(
                product_count=Count(
                    "items__variants",
                    filter=Q(
                        items__is_visible_online=True,
                        items__variants__quantity__gt=0,
                    ),
                ),
                business_count=Count("businesses", filter=Q(businesses__is_active=True)),
            )
            .order_by("-product_count")
        )
        serializer = MarketplaceCategoryTreeSerializer(categories, many=True)
        return Response(serializer.data)


class ReviewViewSet(GenericViewSet, ListModelMixin):
    """
    Public list of reviews with optional filtering by content type + object.
    Creation requires authentication.
    """

    queryset = Review.objects.select_related("reviewer").order_by("-created_at")
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "create":
            return ReviewSerializer
        return ReviewListSerializer

    def get_queryset(self):
        queryset = self.queryset
        model_name = self.request.query_params.get("model")  # "itemvariant" or "business"
        object_id = self.request.query_params.get("object_id")
        if model_name and object_id:
            try:
                ct = ContentType.objects.get(
                    app_label__in=["inventories", "business"], model=model_name
                )
                queryset = queryset.filter(content_type=ct, object_id=object_id)
            except ContentType.DoesNotExist:
                pass
        return queryset

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def submit(self, request):
        """Submit a review. Requires authentication."""
        serializer = ReviewSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()
        return Response(ReviewListSerializer(review).data, status=status.HTTP_201_CREATED)

from decimal import Decimal

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import (
    Avg,
    Count,
    F,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
)
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ReadOnlyModelViewSet

from business.models import Business, Category, Industry
from inventories.models import ItemImage, ItemVariant

from .models import (
    MarketplaceOrder,
    MarketplaceOrderItem,
    Review,
    VariantImage,
)
from .serializers import (
    MarketplaceBusinessDetailSerializer,
    MarketplaceBusinessSerializer,
    MarketplaceCategorySerializer,
    MarketplaceCategoryTreeSerializer,
    MarketplaceIndustrySerializer,
    MarketplaceItemVariantListSerializer,
    MarketplaceItemVariantSerializer,
    MarketplaceSearchSerializer,
    PlaceOrderSerializer,
    ReviewSerializer,
    ReviewSubmitSerializer,
    WaitlistSerializer,
)


def _product_base_queryset():
    """ItemVariant queryset with all marketplace joins/annotations applied."""
    return (
        ItemVariant.objects.select_related(
            "item",
            "item__business",
            "item__business__address",
            "item__business__owner",
        )
        .prefetch_related(
            Prefetch(
                "item__categories",
                queryset=Category.objects.select_related("industry", "image").annotate(
                    _mp_item_count=Count(
                        "items",
                        filter=Q(
                            items__is_visible_online=True,
                            items__variants__quantity__gt=0,
                        ),
                        distinct=True,
                    )
                ),
            ),
            "properties",
            "pricings",
            Prefetch(
                "item__itemimage_set",
                queryset=ItemImage.objects.filter(is_visible=True).select_related(
                    "file"
                ),
            ),
            Prefetch(
                "images",
                queryset=VariantImage.objects.filter(is_visible=True).select_related(
                    "file"
                ),
            ),
            "item__business__categories",
        )
        .annotate(
            avg_rating=Avg("reviews__rating"),
            num_reviews=Count("reviews", distinct=True),
        )
        .filter(item__is_visible_online=True, item__business__is_active=True)
    )


def _price_for_quantity(variant, quantity):
    """Best unit price for a quantity: the bulk tier with the highest
    min_selling_quota that the quantity satisfies, else the variant price."""
    tiers = sorted(
        variant.pricings.all(), key=lambda p: p.min_selling_quota, reverse=True
    )
    for tier in tiers:
        if quantity >= tier.min_selling_quota:
            return Decimal(tier.price)
    if variant.selling_price is not None:
        return Decimal(variant.selling_price)
    return Decimal(tiers[-1].price) if tiers else Decimal("0")


class MarketplaceProductViewSet(ReadOnlyModelViewSet):
    """Marketplace product (ItemVariant) endpoints with filtering and search."""

    queryset = _product_base_queryset()
    permission_classes = [AllowAny]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    search_fields = ["name", "item__name", "item__description", "sku"]
    ordering_fields = ["created_at", "selling_price", "quantity", "name"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return MarketplaceItemVariantListSerializer
        return MarketplaceItemVariantSerializer

    def get_queryset(self):
        queryset = _product_base_queryset()
        params = self.request.query_params

        categories = params.getlist("categories")
        industries = params.getlist("industries")
        businesses = params.getlist("businesses")
        business_types = params.getlist("business_types")
        min_price = params.get("min_price")
        max_price = params.get("max_price")
        in_stock_only = params.get("in_stock_only", "true").lower() == "true"
        min_quantity = params.get("min_quantity")
        verified_only = params.get("verified_only", "false").lower() == "true"
        properties = params.get("properties")  # "color:red,size:large"
        advanced_search = params.get("q")

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
            # NOTE: only single-valued relations here. Including a to-many
            # relation (e.g. properties) in the vector multiplies rows per
            # related object and breaks .distinct(), yielding duplicate products.
            search_vector = (
                SearchVector("name", weight="A")
                + SearchVector("item__name", weight="A")
                + SearchVector("item__description", weight="B")
                + SearchVector("sku", weight="C")
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
                "categories", {"type": "array", "items": {"type": "string"}}
            ),
            OpenApiParameter(
                "industries", {"type": "array", "items": {"type": "string"}}
            ),
            OpenApiParameter(
                "businesses", {"type": "array", "items": {"type": "string"}}
            ),
            OpenApiParameter(
                "business_types", {"type": "array", "items": {"type": "string"}}
            ),
            OpenApiParameter("min_price", OpenApiTypes.DECIMAL),
            OpenApiParameter("max_price", OpenApiTypes.DECIMAL),
            OpenApiParameter("in_stock_only", OpenApiTypes.BOOL),
            OpenApiParameter("min_quantity", OpenApiTypes.INT),
            OpenApiParameter("verified_only", OpenApiTypes.BOOL),
            OpenApiParameter("properties", OpenApiTypes.STR),
            OpenApiParameter("q", OpenApiTypes.STR),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def featured(self, request):
        queryset = (
            self.get_queryset()
            .filter(item__business__is_verified=True, quantity__gt=0)
            .order_by("-created_at")[:20]
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"])
    def trending(self, request):
        queryset = (
            self.get_queryset()
            .filter(quantity__gt=0)
            .order_by("-num_reviews", "-created_at")[:15]
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        queryset = (
            self.get_queryset()
            .filter(quantity__lte=F("item__notify_below"), quantity__gt=0)
            .order_by("quantity")
        )
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=["get"])
    def similar(self, request, pk=None):
        product = self.get_object()
        similar = (
            self.get_queryset()
            .filter(item__categories__in=product.item.categories.all())
            .exclude(id=product.id)
            .distinct()[:10]
        )
        return Response(self.get_serializer(similar, many=True).data)

    @action(detail=True, methods=["get"])
    def reviews(self, request, pk=None):
        product = self.get_object()
        qs = Review.objects.filter(variant=product).order_by("-created_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(ReviewSerializer(page, many=True).data)
        return Response(ReviewSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"])
    def advanced_search(self, request):
        serializer = MarketplaceSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        queryset = self.get_queryset()

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

        queryset = queryset.order_by(data.get("sort_by", "-created_at")).distinct()
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(
                self.get_serializer(page, many=True).data
            )
        return Response(self.get_serializer(queryset, many=True).data)


class MarketplaceCategoryViewSet(ReadOnlyModelViewSet):
    """Category endpoints for the marketplace."""

    queryset = Category.objects.filter(is_active=True).select_related(
        "industry", "image"
    )
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
                items__is_visible_online=True, items__variants__quantity__gt=0
            ).distinct()
        return queryset

    @action(detail=False, methods=["get"])
    def tree(self, request):
        industries = (
            Industry.objects.filter(is_active=True, category__is_active=True)
            .select_related("image")
            .prefetch_related(
                Prefetch(
                    "category_set",
                    queryset=Category.objects.filter(is_active=True).select_related(
                        "image"
                    ),
                    to_attr="active_categories",
                )
            )
            .distinct()
        )
        return Response(MarketplaceIndustrySerializer(industries, many=True).data)


class MarketplaceBusinessViewSet(ReadOnlyModelViewSet):
    """Business (supplier) endpoints for the marketplace."""

    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return MarketplaceBusinessDetailSerializer
        return MarketplaceBusinessSerializer

    def get_queryset(self):
        product_count_sq = (
            ItemVariant.objects.filter(
                item__business=OuterRef("pk"),
                item__is_visible_online=True,
                quantity__gt=0,
            )
            .order_by()
            .values("item__business")
            .annotate(c=Count("*"))
            .values("c")
        )
        queryset = (
            Business.objects.filter(is_active=True)
            .select_related("address", "owner")
            .prefetch_related("categories")
            .annotate(
                avg_rating=Avg("reviews__rating"),
                num_reviews=Count("reviews", distinct=True),
                num_products=Subquery(product_count_sq, output_field=IntegerField()),
            )
        )

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
        self.get_object()  # 404 if missing
        products = _product_base_queryset().filter(item__business_id=pk)

        categories = request.query_params.getlist("categories")
        if categories:
            products = products.filter(item__categories__id__in=categories)
        if request.query_params.get("in_stock_only", "true").lower() == "true":
            products = products.filter(quantity__gt=0)
        products = products.distinct()

        page = self.paginate_queryset(products)
        if page is not None:
            return self.get_paginated_response(
                MarketplaceItemVariantListSerializer(page, many=True).data
            )
        return Response(MarketplaceItemVariantListSerializer(products, many=True).data)

    @action(detail=True, methods=["get"])
    def reviews(self, request, pk=None):
        self.get_object()
        qs = Review.objects.filter(business_id=pk).order_by("-created_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(ReviewSerializer(page, many=True).data)
        return Response(ReviewSerializer(qs, many=True).data)

    @action(detail=True, methods=["post"], permission_classes=[AllowAny])
    def place_order(self, request, pk=None):
        business = self.get_object()
        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        variant_ids = [item["variant_id"] for item in data["items"]]
        variants = {
            v.id: v
            for v in ItemVariant.objects.filter(
                id__in=variant_ids, item__business=business
            ).prefetch_related("pricings")
        }
        missing = [str(vid) for vid in variant_ids if vid not in variants]
        if missing:
            return Response(
                {
                    "detail": f"Variants not found for this supplier: {', '.join(missing)}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        order = MarketplaceOrder.objects.create(
            business=business,
            buyer_name=data["buyer_name"],
            buyer_email=data["buyer_email"],
            buyer_phone=data.get("buyer_phone", ""),
            notes=data.get("notes", ""),
            status="PENDING",
        )
        total = Decimal("0")
        order_items = []
        for line in data["items"]:
            variant = variants[line["variant_id"]]
            qty = line["quantity"]
            unit = _price_for_quantity(variant, qty)
            total += unit * qty
            order_items.append(
                MarketplaceOrderItem(
                    order=order, variant=variant, quantity=qty, price=unit
                )
            )
        MarketplaceOrderItem.objects.bulk_create(order_items)
        order.total_payable = total
        order.save(update_fields=["total_payable", "updated_at"])

        return Response(
            {
                "detail": "Order inquiry submitted. The supplier will contact you shortly.",
                "order_id": str(order.id),
                "status": order.status,
                "total_payable": str(total),
            },
            status=status.HTTP_201_CREATED,
        )


class MarketplaceReviewViewSet(GenericViewSet):
    """Standalone review listing + submission."""

    permission_classes = [AllowAny]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        qs = Review.objects.all().order_by("-created_at")
        business = self.request.query_params.get("business")
        variant = self.request.query_params.get("variant")
        if business:
            qs = qs.filter(business_id=business)
        if variant:
            qs = qs.filter(variant_id=variant)
        return qs

    def list(self, request):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(ReviewSerializer(page, many=True).data)
        return Response(ReviewSerializer(qs, many=True).data)

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def submit(self, request):
        serializer = ReviewSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        model = data["content_type_model"].lower()
        object_id = data["object_id"]
        user = request.user

        review = Review(
            rating=data["rating"],
            title=data.get("title", ""),
            body=data.get("body", ""),
            reviewer=user,
            reviewer_name=(user.get_full_name() or user.first_name or "Anonymous"),
        )

        if model == "business":
            business = Business.objects.filter(id=object_id).first()
            if not business:
                return Response(
                    {"detail": "Business not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            review.business = business
            review.is_verified_purchase = MarketplaceOrder.objects.filter(
                business=business, buyer_email=user.email
            ).exists()
        elif model in ("itemvariant", "item", "product", "variant"):
            variant = ItemVariant.objects.filter(id=object_id).first()
            if not variant:
                return Response(
                    {"detail": "Product not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            review.variant = variant
            review.is_verified_purchase = MarketplaceOrderItem.objects.filter(
                variant=variant, order__buyer_email=user.email
            ).exists()
        else:
            return Response(
                {"detail": f"Unsupported review target '{model}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        review.save()
        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)


class MarketplaceWaitlistViewSet(CreateModelMixin, GenericViewSet):
    """Public waitlist signup."""

    permission_classes = [AllowAny]
    serializer_class = WaitlistSerializer
    queryset = None


class MarketplaceStatsViewSet(GenericViewSet):
    """Marketplace statistics."""

    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def overview(self, request):
        stats = {
            "total_products": ItemVariant.objects.filter(
                item__is_visible_online=True, item__business__is_active=True
            ).count(),
            "total_businesses": Business.objects.filter(is_active=True).count(),
            "total_categories": Category.objects.filter(is_active=True).count(),
            "products_in_stock": ItemVariant.objects.filter(
                item__is_visible_online=True,
                quantity__gt=0,
                item__business__is_active=True,
            ).count(),
            "verified_businesses": Business.objects.filter(
                is_active=True, is_verified=True
            ).count(),
        }
        return Response(stats)

    @action(detail=False, methods=["get"])
    def categories_stats(self, request):
        categories = (
            Category.objects.filter(is_active=True)
            .select_related("industry", "image")
            .annotate(
                _mp_product_count=Count(
                    "items__variants",
                    filter=Q(
                        items__is_visible_online=True,
                        items__variants__quantity__gt=0,
                    ),
                    distinct=True,
                )
            )
            .order_by("-_mp_product_count")
        )
        return Response(MarketplaceCategoryTreeSerializer(categories, many=True).data)

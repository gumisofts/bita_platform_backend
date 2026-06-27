from rest_framework import serializers

from business.models import Address, Business, Category, Industry
from inventories.models import ItemVariant, Pricing, Property

from .models import Review, Waitlist


def file_url(file_meta):
    """Resolve a files.FileMeta (or None) to its public URL."""
    return file_meta.public_url if file_meta else None


# ─── Images ───────────────────────────────────────────────────────────────────


class ImageSerializer(serializers.Serializer):
    """Shared shape for ItemImage / VariantImage -> {id, url, is_primary, is_thumbnail}."""

    id = serializers.UUIDField(read_only=True)
    url = serializers.SerializerMethodField()
    is_primary = serializers.BooleanField(read_only=True)
    is_thumbnail = serializers.BooleanField(read_only=True)

    def get_url(self, obj):
        return file_url(obj.file)


def _visible(images):
    return [img for img in images if getattr(img, "is_visible", True)]


def _pick_thumbnail(images):
    """Return the public URL of the best thumbnail candidate, or None."""
    visible = _visible(images)
    if not visible:
        return None
    for predicate in (lambda i: i.is_thumbnail, lambda i: i.is_primary):
        for img in visible:
            if predicate(img):
                return file_url(img.file)
    return file_url(visible[0].file)


# ─── Categories / Industries ────────────────────────────────────────────────────


class MarketplaceCategorySerializer(serializers.ModelSerializer):
    industry_name = serializers.CharField(
        source="industry.name", read_only=True, default=None
    )
    image = serializers.SerializerMethodField()
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "industry_name", "image", "item_count"]

    def get_image(self, obj):
        return file_url(obj.image)

    def get_item_count(self, obj):
        annotated = getattr(obj, "_mp_item_count", None)
        if annotated is not None:
            return annotated
        return (
            obj.items.filter(is_visible_online=True, variants__quantity__gt=0)
            .distinct()
            .count()
        )


class MarketplaceCategoryTreeSerializer(serializers.ModelSerializer):
    industry = serializers.CharField(
        source="industry.name", read_only=True, default=None
    )
    image = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "industry", "image", "product_count", "is_active"]

    def get_image(self, obj):
        return file_url(obj.image)

    def get_product_count(self, obj):
        annotated = getattr(obj, "_mp_product_count", None)
        if annotated is not None:
            return annotated
        return ItemVariant.objects.filter(
            item__categories=obj, item__is_visible_online=True, quantity__gt=0
        ).count()


class MarketplaceIndustrySerializer(serializers.ModelSerializer):
    # ``active_categories`` is attached via Prefetch in the viewset (only active
    # categories); falls back to all categories if not prefetched.
    categories = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    total_products = serializers.SerializerMethodField()

    class Meta:
        model = Industry
        fields = ["id", "name", "image", "categories", "total_products", "is_active"]

    def get_image(self, obj):
        return file_url(obj.image)

    def get_categories(self, obj):
        cats = getattr(obj, "active_categories", None)
        if cats is None:
            cats = obj.category_set.filter(is_active=True)
        return MarketplaceCategoryTreeSerializer(cats, many=True).data

    def get_total_products(self, obj):
        return ItemVariant.objects.filter(
            item__categories__industry=obj,
            item__is_visible_online=True,
            quantity__gt=0,
        ).count()


# ─── Business ───────────────────────────────────────────────────────────────────


class BusinessCategoryMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "lat",
            "lng",
            "sublocality",
            "locality",
            "admin_2",
            "admin_1",
            "country",
        ]


class MarketplaceBusinessSerializer(serializers.ModelSerializer):
    background_image_url = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    categories = BusinessCategoryMiniSerializer(many=True, read_only=True)
    locality = serializers.SerializerMethodField()
    admin_1 = serializers.SerializerMethodField()
    contact_phone = serializers.SerializerMethodField()
    contact_email = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "business_type",
            "is_verified",
            "background_image_url",
            "average_rating",
            "review_count",
            "product_count",
            "categories",
            "locality",
            "admin_1",
            "contact_phone",
            "contact_email",
        ]

    def get_background_image_url(self, obj):
        return file_url(obj.background_image)

    def get_average_rating(self, obj):
        rating = getattr(obj, "avg_rating", None)
        return round(rating, 1) if rating is not None else None

    def get_review_count(self, obj):
        return getattr(obj, "num_reviews", 0) or 0

    def get_product_count(self, obj):
        return getattr(obj, "num_products", 0) or 0

    def get_locality(self, obj):
        return obj.address.locality if obj.address else None

    def get_admin_1(self, obj):
        return obj.address.admin_1 if obj.address else None

    def get_contact_phone(self, obj):
        return obj.owner.phone_number if obj.owner else None

    def get_contact_email(self, obj):
        return obj.owner.email if obj.owner else None


class MarketplaceBusinessDetailSerializer(MarketplaceBusinessSerializer):
    address = AddressSerializer(read_only=True)

    class Meta(MarketplaceBusinessSerializer.Meta):
        fields = MarketplaceBusinessSerializer.Meta.fields + ["address"]


class ProductBusinessSerializer(serializers.ModelSerializer):
    """Business shape nested inside a product. Cheap to compute (no aggregates);
    counts/rating default to 0/null since product cards only use name + verified."""

    background_image_url = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    categories = BusinessCategoryMiniSerializer(many=True, read_only=True)
    locality = serializers.SerializerMethodField()
    admin_1 = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "business_type",
            "is_verified",
            "background_image_url",
            "average_rating",
            "review_count",
            "product_count",
            "categories",
            "locality",
            "admin_1",
        ]

    def get_background_image_url(self, obj):
        return file_url(obj.background_image)

    def get_average_rating(self, obj):
        return None

    def get_review_count(self, obj):
        return 0

    def get_product_count(self, obj):
        return 0

    def get_locality(self, obj):
        return obj.address.locality if obj.address else None

    def get_admin_1(self, obj):
        return obj.address.admin_1 if obj.address else None


# ─── Variant properties / pricing ───────────────────────────────────────────────


class MarketplacePropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ["id", "name", "value"]


class MarketplacePricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pricing
        fields = ["id", "price", "min_selling_quota"]


# ─── Products (ItemVariant) ──────────────────────────────────────────────────────


class MarketplaceItemVariantListSerializer(serializers.ModelSerializer):
    item_id = serializers.UUIDField(source="item.id", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_description = serializers.CharField(source="item.description", read_only=True)
    inventory_unit = serializers.CharField(source="item.inventory_unit", read_only=True)
    receive_online_orders = serializers.BooleanField(
        source="item.receive_online_orders", read_only=True
    )
    business = ProductBusinessSerializer(source="item.business", read_only=True)
    categories = MarketplaceCategorySerializer(
        source="item.categories", many=True, read_only=True
    )
    thumbnail = serializers.SerializerMethodField()
    pricings = MarketplacePricingSerializer(many=True, read_only=True)
    is_in_stock = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = ItemVariant
        fields = [
            "id",
            "name",
            "quantity",
            "sku",
            "item_id",
            "item_name",
            "item_description",
            "inventory_unit",
            "receive_online_orders",
            "business",
            "categories",
            "thumbnail",
            "pricings",
            "is_in_stock",
            "stock_status",
            "discount_percentage",
            "average_rating",
            "created_at",
        ]

    # ── helpers ──
    def _item_images(self, obj):
        return list(obj.item.itemimage_set.all())

    def _variant_images(self, obj):
        return list(obj.images.all())

    def get_thumbnail(self, obj):
        return _pick_thumbnail(self._variant_images(obj)) or _pick_thumbnail(
            self._item_images(obj)
        )

    def get_is_in_stock(self, obj):
        return obj.quantity > 0

    def get_stock_status(self, obj):
        if obj.quantity == 0:
            return "out_of_stock"
        if obj.quantity <= obj.item.notify_below:
            return "low_stock"
        return "in_stock"

    def get_discount_percentage(self, obj):
        pricings = sorted(obj.pricings.all(), key=lambda p: p.min_selling_quota)
        if len(pricings) > 1:
            highest, lowest = pricings[0].price, pricings[-1].price
            if highest > lowest:
                return round(((highest - lowest) / highest) * 100, 2)
        return 0

    def get_average_rating(self, obj):
        rating = getattr(obj, "avg_rating", None)
        return round(rating, 1) if rating is not None else None


class MarketplaceItemVariantSerializer(MarketplaceItemVariantListSerializer):
    """Full detail serializer."""

    properties = MarketplacePropertySerializer(many=True, read_only=True)
    item_images = serializers.SerializerMethodField()
    item_videos = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    min_selling_quota = serializers.IntegerField(
        source="item.min_selling_quota", read_only=True
    )
    is_returnable = serializers.BooleanField(
        source="item.is_returnable", read_only=True
    )
    is_available_online = serializers.SerializerMethodField()

    class Meta(MarketplaceItemVariantListSerializer.Meta):
        fields = MarketplaceItemVariantListSerializer.Meta.fields + [
            "updated_at",
            "is_default",
            "item_images",
            "item_videos",
            "properties",
            "review_count",
            "is_available_online",
            "min_selling_quota",
            "is_returnable",
        ]

    def get_item_images(self, obj):
        images = _visible(self._variant_images(obj)) + _visible(self._item_images(obj))
        return ImageSerializer(images, many=True).data

    def get_item_videos(self, obj):
        return []

    def get_review_count(self, obj):
        return getattr(obj, "num_reviews", 0) or 0

    def get_is_available_online(self, obj):
        item = obj.item
        return bool(
            item.is_visible_online
            and item.receive_online_orders
            and obj.quantity > 0
            and item.business.is_active
        )


# ─── Reviews ────────────────────────────────────────────────────────────────────


class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = [
            "id",
            "rating",
            "title",
            "body",
            "is_verified_purchase",
            "reviewer_name",
            "created_at",
        ]


class ReviewSubmitSerializer(serializers.Serializer):
    content_type_model = serializers.CharField()
    object_id = serializers.UUIDField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    title = serializers.CharField(required=False, allow_blank=True, default="")
    body = serializers.CharField(required=False, allow_blank=True, default="")


# ─── Waitlist ───────────────────────────────────────────────────────────────────


class WaitlistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Waitlist
        fields = ["id", "email", "full_name", "business_name", "phone"]
        extra_kwargs = {
            "full_name": {"required": False},
            "business_name": {"required": False},
            "phone": {"required": False},
        }

    def create(self, validated_data):
        # Idempotent: a repeated signup updates the stored details instead of 400ing.
        obj, _ = Waitlist.objects.update_or_create(
            email=validated_data["email"],
            defaults={k: v for k, v in validated_data.items() if k != "email"},
        )
        return obj


# ─── Orders ─────────────────────────────────────────────────────────────────────


class PlaceOrderItemSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class PlaceOrderSerializer(serializers.Serializer):
    buyer_name = serializers.CharField()
    buyer_email = serializers.EmailField()
    buyer_phone = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = PlaceOrderItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value


# ─── Search (kept for the advanced_search action) ────────────────────────────────


class MarketplaceSearchSerializer(serializers.Serializer):
    query = serializers.CharField(required=False, allow_blank=True)
    categories = serializers.ListField(
        child=serializers.UUIDField(), required=False, allow_empty=True
    )
    business_types = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )
    min_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    max_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False
    )
    in_stock_only = serializers.BooleanField(default=True)
    verified_businesses_only = serializers.BooleanField(default=False)
    sort_by = serializers.ChoiceField(
        choices=[
            "created_at",
            "-created_at",
            "name",
            "-name",
            "quantity",
            "-quantity",
        ],
        default="-created_at",
    )

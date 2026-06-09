from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Avg, Count, Q
from rest_framework import serializers

from business.models import Address, Business, Category, Industry
from crms.models import Customer
from files.models import FileMeta
from inventories.models import Item, ItemImage, ItemVariant, ItemVideo, Pricing, Property
from orders.models import Order, OrderItem

from .models import Review


# ─── Address ─────────────────────────────────────────────────────────────────


class MarketplaceAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["lat", "lng", "sublocality", "locality", "admin_2", "admin_1", "country"]


# ─── Business ────────────────────────────────────────────────────────────────


class MarketplaceBusinessSerializer(serializers.ModelSerializer):
    """Full business serializer for marketplace detail pages."""

    address = MarketplaceAddressSerializer(read_only=True)
    background_image_url = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()

    class Meta:
        model = Business
        fields = [
            "id",
            "name",
            "business_type",
            "is_verified",
            "is_active",
            "address",
            "background_image_url",
            "contact_phone",
            "contact_email",
            "average_rating",
            "review_count",
            "product_count",
            "categories",
        ]

    def get_background_image_url(self, obj):
        if obj.background_image:
            return obj.background_image.public_url
        return None

    def get_average_rating(self, obj):
        ct = ContentType.objects.get_for_model(Business)
        result = Review.objects.filter(content_type=ct, object_id=obj.id).aggregate(
            avg=Avg("rating")
        )
        return round(result["avg"], 1) if result["avg"] else None

    def get_review_count(self, obj):
        ct = ContentType.objects.get_for_model(Business)
        return Review.objects.filter(content_type=ct, object_id=obj.id).count()

    def get_product_count(self, obj):
        return ItemVariant.objects.filter(
            item__business=obj,
            item__is_visible_online=True,
            item__is_active=True,
            quantity__gt=0,
        ).count()

    def get_categories(self, obj):
        return [{"id": str(c.id), "name": c.name} for c in obj.categories.all()]


class MarketplaceBusinessListSerializer(serializers.ModelSerializer):
    """Compact business serializer for list views."""

    background_image_url = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    product_count = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    locality = serializers.CharField(source="address.locality", read_only=True, default=None)
    admin_1 = serializers.CharField(source="address.admin_1", read_only=True, default=None)

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
        if obj.background_image:
            return obj.background_image.public_url
        return None

    def get_average_rating(self, obj):
        ct = ContentType.objects.get_for_model(Business)
        result = Review.objects.filter(content_type=ct, object_id=obj.id).aggregate(
            avg=Avg("rating")
        )
        return round(result["avg"], 1) if result["avg"] else None

    def get_review_count(self, obj):
        ct = ContentType.objects.get_for_model(Business)
        return Review.objects.filter(content_type=ct, object_id=obj.id).count()

    def get_product_count(self, obj):
        return ItemVariant.objects.filter(
            item__business=obj,
            item__is_visible_online=True,
            item__is_active=True,
            quantity__gt=0,
        ).count()

    def get_categories(self, obj):
        return [{"id": str(c.id), "name": c.name} for c in obj.categories.all()]


# ─── Category / Industry ─────────────────────────────────────────────────────


class MarketplaceCategorySerializer(serializers.ModelSerializer):
    industry_name = serializers.CharField(source="industry.name", read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "industry_name", "image", "item_count"]

    def get_item_count(self, obj):
        return (
            obj.items.filter(variants__quantity__gt=0, is_visible_online=True)
            .distinct()
            .count()
        )


# ─── Item Images & Videos ─────────────────────────────────────────────────────


class MarketplaceItemImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ItemImage
        fields = ["id", "url", "is_primary", "is_thumbnail"]

    def get_url(self, obj):
        return obj.file.public_url if obj.file else None


class MarketplaceItemVideoSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ItemVideo
        fields = ["id", "url", "is_primary"]

    def get_url(self, obj):
        return obj.file.public_url if obj.file else None


# ─── Properties & Pricing ────────────────────────────────────────────────────


class MarketplacePropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        fields = ["id", "name", "value"]


class MarketplacePricingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pricing
        fields = ["id", "price", "min_selling_quota"]


# ─── Reviews ─────────────────────────────────────────────────────────────────


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()

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
            # write-only fields for creation
            "content_type_model",
            "object_id",
        ]
        extra_kwargs = {
            "content_type_model": {"write_only": True},
            "object_id": {"write_only": True},
        }

    content_type_model = serializers.ChoiceField(
        choices=["itemvariant", "business"],
        write_only=True,
    )
    object_id = serializers.UUIDField(write_only=True)

    def get_reviewer_name(self, obj):
        user = obj.reviewer
        name = user.first_name or ""
        if user.last_name:
            name = f"{name} {user.last_name}".strip()
        return name or str(user.id)

    def create(self, validated_data):
        model_name = validated_data.pop("content_type_model")
        object_id = validated_data.pop("object_id")
        ct = ContentType.objects.get(app_label__in=["inventories", "business"], model=model_name)
        validated_data["content_type"] = ct
        validated_data["object_id"] = object_id
        validated_data["reviewer"] = self.context["request"].user
        return super().create(validated_data)


class ReviewListSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "rating", "title", "body", "is_verified_purchase", "reviewer_name", "created_at"]

    def get_reviewer_name(self, obj):
        user = obj.reviewer
        name = user.first_name or ""
        if user.last_name:
            name = f"{name} {user.last_name}".strip()
        return name or str(user.id)


# ─── Product (ItemVariant) ────────────────────────────────────────────────────


class MarketplaceItemVariantSerializer(serializers.ModelSerializer):
    """Full ItemVariant serializer for marketplace product detail."""

    item_id = serializers.UUIDField(source="item.id", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_description = serializers.CharField(source="item.description", read_only=True)
    inventory_unit = serializers.CharField(source="item.inventory_unit", read_only=True)
    receive_online_orders = serializers.BooleanField(source="item.receive_online_orders", read_only=True)
    min_selling_quota = serializers.IntegerField(source="item.min_selling_quota", read_only=True)
    is_returnable = serializers.BooleanField(source="item.is_returnable", read_only=True)

    business = MarketplaceBusinessListSerializer(source="item.business", read_only=True)
    categories = MarketplaceCategorySerializer(source="item.categories", many=True, read_only=True)

    item_images = serializers.SerializerMethodField()
    item_videos = serializers.SerializerMethodField()
    properties = MarketplacePropertySerializer(many=True, read_only=True)
    pricings = MarketplacePricingSerializer(many=True, read_only=True)

    is_in_stock = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    is_available_online = serializers.SerializerMethodField()

    class Meta:
        model = ItemVariant
        fields = [
            "id",
            "name",
            "selling_price",
            "quantity",
            "sku",
            "is_default",
            "created_at",
            "updated_at",
            # item fields
            "item_id",
            "item_name",
            "item_description",
            "inventory_unit",
            "receive_online_orders",
            "min_selling_quota",
            "is_returnable",
            # relations
            "business",
            "categories",
            "item_images",
            "item_videos",
            "properties",
            "pricings",
            # computed
            "is_in_stock",
            "stock_status",
            "discount_percentage",
            "average_rating",
            "review_count",
            "is_available_online",
        ]

    def get_item_images(self, obj):
        images = ItemImage.objects.filter(item=obj.item, is_visible=True)
        return MarketplaceItemImageSerializer(images, many=True).data

    def get_item_videos(self, obj):
        videos = ItemVideo.objects.filter(item=obj.item, is_visible=True)
        return MarketplaceItemVideoSerializer(videos, many=True).data

    def get_is_in_stock(self, obj):
        return obj.quantity > 0

    def get_stock_status(self, obj):
        if obj.quantity == 0:
            return "out_of_stock"
        elif obj.quantity <= obj.item.notify_below:
            return "low_stock"
        return "in_stock"

    def get_discount_percentage(self, obj):
        pricings = list(obj.pricings.order_by("min_selling_quota"))
        if len(pricings) > 1:
            highest = pricings[0].price
            lowest = pricings[-1].price
            if highest > lowest:
                return round(((highest - lowest) / highest) * 100, 2)
        return 0

    def get_average_rating(self, obj):
        ct = ContentType.objects.get_for_model(ItemVariant)
        result = Review.objects.filter(content_type=ct, object_id=obj.id).aggregate(
            avg=Avg("rating")
        )
        return round(result["avg"], 1) if result["avg"] else None

    def get_review_count(self, obj):
        ct = ContentType.objects.get_for_model(ItemVariant)
        return Review.objects.filter(content_type=ct, object_id=obj.id).count()

    def get_is_available_online(self, obj):
        return (
            obj.item.is_visible_online
            and obj.item.receive_online_orders
            and obj.quantity > 0
            and obj.item.is_active
            and obj.item.business.is_active
        )


class MarketplaceItemVariantListSerializer(serializers.ModelSerializer):
    """Compact variant serializer for product listing cards."""

    item_id = serializers.UUIDField(source="item.id", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_description = serializers.CharField(source="item.description", read_only=True)
    inventory_unit = serializers.CharField(source="item.inventory_unit", read_only=True)
    receive_online_orders = serializers.BooleanField(source="item.receive_online_orders", read_only=True)

    business = MarketplaceBusinessListSerializer(source="item.business", read_only=True)
    categories = MarketplaceCategorySerializer(source="item.categories", many=True, read_only=True)

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
            "selling_price",
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

    def get_thumbnail(self, obj):
        img = ItemImage.objects.filter(item=obj.item, is_visible=True, is_thumbnail=True).first()
        if not img:
            img = ItemImage.objects.filter(item=obj.item, is_visible=True, is_primary=True).first()
        if not img:
            img = ItemImage.objects.filter(item=obj.item, is_visible=True).first()
        if img:
            return img.file.public_url
        return None

    def get_is_in_stock(self, obj):
        return obj.quantity > 0

    def get_stock_status(self, obj):
        if obj.quantity == 0:
            return "out_of_stock"
        elif obj.quantity <= obj.item.notify_below:
            return "low_stock"
        return "in_stock"

    def get_discount_percentage(self, obj):
        pricings = list(obj.pricings.order_by("min_selling_quota"))
        if len(pricings) > 1:
            highest = pricings[0].price
            lowest = pricings[-1].price
            if highest > lowest:
                return round(((highest - lowest) / highest) * 100, 2)
        return 0

    def get_average_rating(self, obj):
        ct = ContentType.objects.get_for_model(ItemVariant)
        result = Review.objects.filter(content_type=ct, object_id=obj.id).aggregate(
            avg=Avg("rating")
        )
        return round(result["avg"], 1) if result["avg"] else None


# ─── Marketplace Search ───────────────────────────────────────────────────────


class MarketplaceSearchSerializer(serializers.Serializer):
    query = serializers.CharField(required=False, allow_blank=True)
    categories = serializers.ListField(child=serializers.UUIDField(), required=False, allow_empty=True)
    business_types = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    max_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    in_stock_only = serializers.BooleanField(default=True)
    verified_businesses_only = serializers.BooleanField(default=False)
    sort_by = serializers.ChoiceField(
        choices=[
            "created_at", "-created_at",
            "selling_price", "-selling_price",
            "name", "-name",
            "quantity", "-quantity",
        ],
        default="-created_at",
    )


# ─── Category Tree ────────────────────────────────────────────────────────────


class MarketplaceCategoryTreeSerializer(serializers.ModelSerializer):
    industry = serializers.CharField(source="industry.name", read_only=True)
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "industry", "image", "product_count", "is_active"]

    def get_product_count(self, obj):
        return ItemVariant.objects.filter(
            item__categories=obj, item__is_visible_online=True, quantity__gt=0
        ).count()


class MarketplaceIndustrySerializer(serializers.ModelSerializer):
    categories = MarketplaceCategoryTreeSerializer(source="category_set", many=True, read_only=True)
    total_products = serializers.SerializerMethodField()

    class Meta:
        model = Industry
        fields = ["id", "name", "image", "categories", "total_products", "is_active"]

    def get_total_products(self, obj):
        return ItemVariant.objects.filter(
            item__categories__industry=obj,
            item__is_visible_online=True,
            quantity__gt=0,
        ).count()


# ─── Marketplace Order ────────────────────────────────────────────────────────


class MarketplaceOrderItemInputSerializer(serializers.Serializer):
    variant_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1)


class MarketplaceOrderCreateSerializer(serializers.Serializer):
    """
    Creates a Customer (if needed) and a real Order record for a marketplace buyer.
    The order is linked to the first branch of the target business.
    """

    buyer_name = serializers.CharField(max_length=255)
    buyer_email = serializers.EmailField()
    buyer_phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    items = MarketplaceOrderItemInputSerializer(many=True, min_length=1)

    def validate(self, attrs):
        items = attrs["items"]
        validated_items = []
        for entry in items:
            try:
                variant = ItemVariant.objects.select_related("item", "item__business", "item__branch").get(
                    id=entry["variant_id"],
                    item__is_active=True,
                    item__is_visible_online=True,
                    item__business__is_active=True,
                )
            except ItemVariant.DoesNotExist:
                raise serializers.ValidationError(
                    {"items": f"Product variant {entry['variant_id']} not found or not available."}
                )
            if variant.quantity < entry["quantity"]:
                raise serializers.ValidationError(
                    {"items": f"Insufficient stock for '{variant.name}'. Available: {variant.quantity}."}
                )
            validated_items.append({"variant": variant, "quantity": entry["quantity"]})
        attrs["_validated_items"] = validated_items
        return attrs

    @transaction.atomic
    def create_order(self, business):
        data = self.validated_data
        validated_items = data["_validated_items"]

        # All variants must belong to the target business
        for entry in validated_items:
            if entry["variant"].item.business_id != business.id:
                raise serializers.ValidationError(
                    {"items": "All items must belong to the same business."}
                )

        branch = business.branches.first()
        if not branch:
            raise serializers.ValidationError({"business": "This business has no active branch."})

        # Create or retrieve CRM customer
        customer, _ = Customer.objects.get_or_create(
            email=data["buyer_email"],
            business=business,
            defaults={"full_name": data["buyer_name"]},
        )

        total_payable = sum(
            (entry["variant"].selling_price or 0) * entry["quantity"]
            for entry in validated_items
        )

        order = Order.objects.create(
            customer=customer,
            business=business,
            branch=branch,
            total_payable=total_payable,
            status=Order.StatusChoices.PENDING,
            additional_info={
                "source": "marketplace",
                "buyer_name": data["buyer_name"],
                "buyer_phone": data.get("buyer_phone", ""),
                "notes": data.get("notes", ""),
            },
        )

        for entry in validated_items:
            OrderItem.objects.create(
                order=order,
                variant=entry["variant"],
                quantity=entry["quantity"],
                price=entry["variant"].selling_price or 0,
            )

        return order

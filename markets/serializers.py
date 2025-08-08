from django.db.models import Avg, Count, Q
from rest_framework import serializers

from business.models import Business, Category, Industry
from files.models import FileMeta
from inventories.models import Item, ItemImage, ItemVariant, Pricing, Property


class MarketplaceBusinessSerializer(serializers.ModelSerializer):
    """Simplified business serializer for marketplace"""

    class Meta:
        model = Business
        fields = ["id", "name", "business_type", "is_verified"]


class MarketplaceCategorySerializer(serializers.ModelSerializer):
    """Category serializer with industry information"""

    industry_name = serializers.CharField(source="industry.name", read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "industry_name", "image", "item_count"]

    def get_item_count(self, obj):
        return (
            obj.items.filter(variants__is_visible_online=True, variants__quantity__gt=0)
            .distinct()
            .count()
        )


class MarketplaceItemImageSerializer(serializers.ModelSerializer):
    """Item image serializer for marketplace"""

    class Meta:
        model = ItemImage
        fields = ["id", "file", "is_primary", "is_thumbnail"]


class MarketplacePropertySerializer(serializers.ModelSerializer):
    """Property serializer for item variants"""

    class Meta:
        model = Property
        fields = ["id", "name", "value"]


class MarketplacePricingSerializer(serializers.ModelSerializer):
    """Pricing serializer for different quantities"""

    class Meta:
        model = Pricing
        fields = ["id", "price", "min_selling_quota"]


class MarketplaceItemVariantSerializer(serializers.ModelSerializer):
    """Comprehensive ItemVariant serializer for marketplace"""

    # Item information
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_description = serializers.CharField(source="item.description", read_only=True)
    item_images = serializers.SerializerMethodField()
    inventory_unit = serializers.CharField(source="item.inventory_unit", read_only=True)

    # Business information
    business = MarketplaceBusinessSerializer(source="item.business", read_only=True)

    # Categories
    categories = MarketplaceCategorySerializer(
        source="item.categories", many=True, read_only=True
    )

    # Variant properties
    properties = MarketplacePropertySerializer(many=True, read_only=True)

    # Pricing information
    pricings = MarketplacePricingSerializer(many=True, read_only=True)

    # Calculated fields
    is_in_stock = serializers.SerializerMethodField()
    stock_status = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    # Marketplace specific fields
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
            # Item fields
            "item_name",
            "item_description",
            "item_images",
            "inventory_unit",
            # Business
            "business",
            # Categories
            "categories",
            # Properties
            "properties",
            # Pricing
            "pricings",
            # Calculated fields
            "is_in_stock",
            "stock_status",
            "discount_percentage",
            "average_rating",
            "is_available_online",
        ]

    def get_item_images(self, obj):
        images = ItemImage.objects.filter(item=obj.item, is_visible=True)
        return MarketplaceItemImageSerializer(images, many=True).data

    def get_is_in_stock(self, obj):
        return obj.quantity > 0

    def get_stock_status(self, obj):
        if obj.quantity == 0:
            return "out_of_stock"
        elif obj.quantity <= obj.notify_below:
            return "low_stock"
        else:
            return "in_stock"

    def get_discount_percentage(self, obj):
        # Calculate discount if there are pricing tiers
        pricings = obj.pricings.all().order_by("min_selling_quota")
        if pricings.count() > 1:
            highest_price = pricings.first().price
            lowest_price = pricings.last().price
            if highest_price > lowest_price:
                return round(((highest_price - lowest_price) / highest_price) * 100, 2)
        return 0

    def get_average_rating(self, obj):
        # Placeholder for future rating system
        return None

    def get_is_available_online(self, obj):
        return (
            obj.is_visible_online
            and obj.receive_online_orders
            and obj.quantity > 0
            and obj.item.business.is_active
        )


class MarketplaceItemVariantListSerializer(MarketplaceItemVariantSerializer):
    """Simplified serializer for list views with essential information"""

    class Meta(MarketplaceItemVariantSerializer.Meta):
        fields = [
            "id",
            "name",
            "selling_price",
            "quantity",
            "sku",
            "item_name",
            "item_description",
            "inventory_unit",
            "business",
            "categories",
            "item_images",
            "is_in_stock",
            "stock_status",
            "discount_percentage",
            "created_at",
        ]


class MarketplaceSearchSerializer(serializers.Serializer):
    """Serializer for search parameters"""

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
            "selling_price",
            "-selling_price",
            "name",
            "-name",
            "quantity",
            "-quantity",
        ],
        default="-created_at",
    )


class MarketplaceCategoryTreeSerializer(serializers.ModelSerializer):
    """Category serializer with hierarchical structure"""

    industry = serializers.CharField(source="industry.name", read_only=True)
    product_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ["id", "name", "industry", "image", "product_count", "is_active"]

    def get_product_count(self, obj):
        return ItemVariant.objects.filter(
            item__categories=obj, is_visible_online=True, quantity__gt=0
        ).count()


class MarketplaceIndustrySerializer(serializers.ModelSerializer):
    """Industry serializer with categories"""

    categories = MarketplaceCategoryTreeSerializer(
        source="category_set", many=True, read_only=True
    )
    total_products = serializers.SerializerMethodField()

    class Meta:
        model = Industry
        fields = ["id", "name", "image", "categories", "total_products", "is_active"]

    def get_total_products(self, obj):
        return ItemVariant.objects.filter(
            item__categories__industry=obj, is_visible_online=True, quantity__gt=0
        ).count()

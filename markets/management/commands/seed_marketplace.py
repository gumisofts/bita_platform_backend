"""Seed a rich marketplace demo dataset.

Creates industries, categories, supplier businesses (with owners, addresses,
branches), products (items + variants with bulk pricing tiers, properties and
images), reviews, a sample order, and a few waitlist entries.

Every random-looking choice is derived deterministically from a stable string
key (not a shared RNG stream), so the command is fully idempotent: re-running it
reuses existing rows and never creates duplicates. Use ``--flush`` to remove
previously seeded demo data first.

    env/bin/python manage.py seed_marketplace
    env/bin/python manage.py seed_marketplace --flush
"""

import hashlib
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from business.models import Address, Branch, Business, Category, Industry
from files.models import FileMeta
from inventories.models import Item, ItemImage, ItemVariant, Pricing, Property
from markets.models import (
    MarketplaceOrder,
    MarketplaceOrderItem,
    Review,
    VariantImage,
    Waitlist,
)

User = get_user_model()


def _h(key):
    return int(hashlib.md5(str(key).encode()).hexdigest(), 16)


def dchoice(key, seq):
    """Deterministic choice from a sequence, keyed on a stable string."""
    return seq[_h(key) % len(seq)]


def dfloat(key, lo, hi):
    """Deterministic float in [lo, hi], keyed on a stable string."""
    return lo + (_h(key) % 10001) / 10000 * (hi - lo)


# ─── Catalog data ────────────────────────────────────────────────────────────

INDUSTRIES = {
    "Food & Beverage": [
        "Grains & Cereals",
        "Cooking Oils",
        "Beverages",
        "Spices & Seasonings",
        "Dairy",
    ],
    "Construction & Hardware": [
        "Cement & Aggregates",
        "Steel & Rebar",
        "Paints & Coatings",
        "Plumbing",
    ],
    "Textiles & Apparel": [
        "Fabrics",
        "Ready-made Garments",
        "Footwear",
    ],
}

# category -> list of (product_name, unit, base_price, properties)
PRODUCTS = {
    "Grains & Cereals": [
        (
            "White Teff (Magna)",
            "quintal",
            8500,
            [("Grade", "Magna"), ("Origin", "Gojjam")],
        ),
        ("Red Teff", "quintal", 7200, [("Grade", "Sergegna")]),
        ("Wheat Flour", "50kg sack", 3900, [("Type", "All-purpose")]),
        ("Maize", "quintal", 4200, [("Moisture", "13%")]),
        ("Red Lentils", "quintal", 9800, [("Grade", "Premium")]),
    ],
    "Cooking Oils": [
        ("Sunflower Oil", "20L jerrycan", 3200, [("Purity", "100%")]),
        ("Palm Oil", "20L jerrycan", 2800, [("Type", "Refined")]),
        ("Niger Seed Oil", "5L bottle", 1450, [("Cold-pressed", "Yes")]),
    ],
    "Beverages": [
        ("Bottled Water (24-pack)", "case", 360, [("Volume", "600ml")]),
        ("Soft Drink Assorted", "case", 720, [("Bottles", "24")]),
        ("Ground Coffee", "kg", 920, [("Roast", "Medium"), ("Region", "Yirgacheffe")]),
    ],
    "Spices & Seasonings": [
        ("Berbere Blend", "kg", 640, [("Heat", "Hot")]),
        ("Mitmita", "kg", 880, [("Heat", "Very Hot")]),
        ("Turmeric Powder", "kg", 410, [("Grade", "A")]),
    ],
    "Dairy": [
        ("Pasteurized Milk (12-pack)", "case", 540, [("Volume", "1L")]),
        ("Table Butter", "kg", 760, [("Type", "Unsalted")]),
    ],
    "Cement & Aggregates": [
        ("Portland Cement (OPC)", "50kg bag", 1050, [("Grade", "42.5R")]),
        ("Coarse Aggregate", "m3", 950, [("Size", "20mm")]),
        ("River Sand", "m3", 700, [("Wash", "Washed")]),
    ],
    "Steel & Rebar": [
        (
            "Deformed Rebar 12mm",
            "12m bar",
            1180,
            [("Diameter", "12mm"), ("Standard", "ES")],
        ),
        ("Deformed Rebar 16mm", "12m bar", 2050, [("Diameter", "16mm")]),
        ("Steel Wire Mesh", "sheet", 1650, [("Gauge", "8")]),
    ],
    "Paints & Coatings": [
        ("Interior Emulsion Paint", "20L bucket", 4200, [("Finish", "Matte")]),
        ("Exterior Weather Paint", "20L bucket", 5600, [("Finish", "Satin")]),
    ],
    "Plumbing": [
        ("PPR Pipe 25mm", "4m length", 280, [("Pressure", "PN20")]),
        ("PVC Fittings Kit", "box", 640, [("Pieces", "50")]),
    ],
    "Fabrics": [
        (
            "Cotton Shema Fabric",
            "roll",
            4800,
            [("Width", "1.5m"), ("Color", "Natural")],
        ),
        ("Polyester Suiting", "roll", 5200, [("Color", "Navy")]),
    ],
    "Ready-made Garments": [
        ("Men's Cotton Shirts (dozen)", "dozen", 5400, [("Size", "Mixed")]),
        ("Children's School Uniform", "set", 620, [("Color", "Blue")]),
        ("Habesha Kemis", "piece", 3200, [("Style", "Hand-woven")]),
    ],
    "Footwear": [
        (
            "Leather Loafers (dozen)",
            "dozen",
            9600,
            [("Color", "Brown"), ("Material", "Leather")],
        ),
        ("Canvas Sneakers (dozen)", "dozen", 6400, [("Color", "White")]),
    ],
}

# business name, type, verified, list of categories, subcity (locality)
BUSINESSES = [
    (
        "Abyssinia Grains Wholesale",
        "whole_sale",
        True,
        ["Grains & Cereals", "Spices & Seasonings"],
        "Addis Ketema",
    ),
    (
        "Habesha Edible Oils",
        "manufacturing",
        True,
        ["Cooking Oils"],
        "Nifas Silk-Lafto",
    ),
    (
        "Sheger Beverages Distribution",
        "whole_sale",
        True,
        ["Beverages", "Dairy"],
        "Kirkos",
    ),
    (
        "Dire Construction Supplies",
        "whole_sale",
        True,
        ["Cement & Aggregates", "Steel & Rebar"],
        "Yeka",
    ),
    (
        "Sabean Steel & Hardware",
        "manufacturing",
        True,
        ["Steel & Rebar", "Plumbing", "Paints & Coatings"],
        "Akaki Kaliti",
    ),
    (
        "Merkato Textiles",
        "whole_sale",
        True,
        ["Fabrics", "Ready-made Garments"],
        "Addis Ketema",
    ),
    (
        "Lalibela Garments",
        "manufacturing",
        False,
        ["Ready-made Garments", "Footwear"],
        "Bole",
    ),
    (
        "Addis Fresh Distributors",
        "retail",
        False,
        ["Dairy", "Spices & Seasonings", "Beverages"],
        "Lideta",
    ),
]

REVIEW_SNIPPETS = [
    (
        5,
        "Excellent quality",
        "Consistent quality and on-time delivery. Highly recommended.",
    ),
    (4, "Good supplier", "Fair pricing and responsive team. Will order again."),
    (
        5,
        "Reliable wholesale partner",
        "Bulk pricing is competitive and stock is always available.",
    ),
    (3, "Decent", "Product is fine but delivery took a little longer than expected."),
    (
        4,
        "Great bulk deals",
        "The volume discounts make a real difference for our shop.",
    ),
]

FIRST_NAMES = [
    "Abebe",
    "Marta",
    "Dawit",
    "Hanna",
    "Yonas",
    "Selam",
    "Bereket",
    "Tigist",
    "Samuel",
    "Liya",
]
LAST_NAMES = [
    "Tadesse",
    "Kebede",
    "Bekele",
    "Girma",
    "Alemu",
    "Haile",
    "Mengistu",
    "Worku",
]


class Command(BaseCommand):
    help = "Seed a rich marketplace demo dataset (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete previously seeded demo data before seeding.",
        )

    def img(self, key, w=800, h=800):
        """get_or_create a FileMeta pointing at a deterministic placeholder image."""
        url = f"https://picsum.photos/seed/{slugify(key)}/{w}/{h}"
        fm, _ = FileMeta.objects.get_or_create(
            key=f"seed/{slugify(key)}", defaults={"public_url": url}
        )
        if fm.public_url != url:
            fm.public_url = url
            fm.save(update_fields=["public_url"])
        return fm

    @transaction.atomic
    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()

        # ── Industries + categories ──
        categories = {}
        for ind_name, cats in INDUSTRIES.items():
            industry, _ = Industry.objects.get_or_create(
                name=ind_name, defaults={"is_active": True}
            )
            if not industry.image:
                industry.image = self.img(f"industry-{ind_name}", 1200, 600)
                industry.save(update_fields=["image"])
            for cat_name in cats:
                cat, _ = Category.objects.get_or_create(
                    name=cat_name, industry=industry, defaults={"is_active": True}
                )
                if not cat.image:
                    cat.image = self.img(f"category-{cat_name}", 600, 600)
                    cat.save(update_fields=["image"])
                categories[cat_name] = cat
        self.stdout.write(
            f"Industries: {Industry.objects.count()}, Categories: {Category.objects.count()}"
        )

        # ── Businesses ──
        businesses = []
        for i, (name, btype, verified, cat_names, subcity) in enumerate(
            BUSINESSES, start=1
        ):
            owner = self._owner(i, name)
            business = Business.objects.filter(name=name).first()
            if business is None:
                # Address is a OneToOneField on Business -> create a fresh one each time.
                address = Address.objects.create(
                    admin_1="Addis Ababa",
                    locality=subcity,
                    country="Ethiopia",
                    lat=dfloat(f"lat-{name}", 8.95, 9.05),
                    lng=dfloat(f"lng-{name}", 38.70, 38.80),
                    sublocality=f"{subcity} District",
                )
                business = Business.objects.create(
                    name=name,
                    owner=owner,
                    business_type=btype,
                    address=address,
                    is_verified=verified,
                    is_active=True,
                    background_image=self.img(f"business-{name}", 1200, 400),
                )
            else:
                address = business.address
                if not business.background_image:
                    business.background_image = self.img(f"business-{name}", 1200, 400)
                    business.save(update_fields=["background_image"])
            business.categories.set([categories[c] for c in cat_names])
            branch, _ = Branch.objects.get_or_create(
                name="Main Branch", business=business, defaults={"address": address}
            )
            businesses.append((business, branch, cat_names))
        seeded_names = [b[0] for b in BUSINESSES]
        self.stdout.write(
            f"Businesses: {Business.objects.filter(name__in=seeded_names).count()}"
        )

        # ── Items + variants ──
        all_variants = []
        for business, branch, cat_names in businesses:
            biz_slug = slugify(business.name)
            for cat_name in cat_names:
                for prod_name, unit, base_price, props in PRODUCTS.get(cat_name, [])[
                    :3
                ]:
                    item, _ = Item.objects.get_or_create(
                        business=business,
                        name=prod_name,
                        defaults={
                            "branch": branch,
                            "inventory_unit": unit,
                            "description": (
                                f"Wholesale {prod_name} supplied by {business.name}. "
                                "Bulk quantities available with tiered pricing."
                            ),
                            "min_selling_quota": 1,
                            "notify_below": 10,
                            "receive_online_orders": True,
                            "is_active": True,
                            "is_returnable": dchoice(
                                f"ret-{biz_slug}-{prod_name}", [True, False]
                            ),
                            "is_visible_online": True,
                        },
                    )
                    item.categories.set([categories[cat_name]])
                    if not item.itemimage_set.exists():
                        ItemImage.objects.create(
                            item=item,
                            file=self.img(f"item-{biz_slug}-{prod_name}"),
                            is_primary=True,
                            is_thumbnail=True,
                            is_visible=True,
                        )
                        ItemImage.objects.create(
                            item=item,
                            file=self.img(f"item-{biz_slug}-{prod_name}-2"),
                            is_visible=True,
                        )

                    n_variants = dchoice(f"nv-{biz_slug}-{prod_name}", [1, 1, 2])
                    for vi in range(n_variants):
                        sku = f"{biz_slug}-{slugify(prod_name)}-{vi}"
                        price = (
                            Decimal(base_price)
                            * (Decimal("1.0") + Decimal(vi) * Decimal("0.08"))
                        ).quantize(Decimal("1."))
                        vname = prod_name if vi == 0 else f"{prod_name} (Premium)"
                        variant, _ = ItemVariant.objects.get_or_create(
                            sku=sku,
                            defaults={
                                "item": item,
                                "name": vname,
                                "selling_price": price,
                                "quantity": dchoice(
                                    f"qty-{sku}", [0, 8, 25, 60, 140, 300]
                                ),
                                "is_default": vi == 0,
                            },
                        )
                        if not variant.pricings.exists():
                            base = int(price)
                            Pricing.objects.create(
                                item_variant=variant, min_selling_quota=1, price=base
                            )
                            Pricing.objects.create(
                                item_variant=variant,
                                min_selling_quota=10,
                                price=int(base * 0.92),
                            )
                            Pricing.objects.create(
                                item_variant=variant,
                                min_selling_quota=50,
                                price=int(base * 0.85),
                            )
                        if not variant.properties.exists():
                            for pname, pval in props:
                                Property.objects.create(
                                    item_variant=variant, name=pname, value=pval
                                )
                        if (
                            vi == 0
                            and _h(f"img-{sku}") % 2 == 0
                            and not variant.images.exists()
                        ):
                            VariantImage.objects.create(
                                variant=variant,
                                file=self.img(f"variant-{sku}"),
                                is_primary=True,
                                is_thumbnail=True,
                                is_visible=True,
                            )
                        all_variants.append(variant)
        self.stdout.write(
            f"Items: {Item.objects.count()}, Variants: {ItemVariant.objects.count()}"
        )

        # ── Reviewers + reviews (deterministic counts/targets) ──
        reviewers = [self._buyer(i) for i in range(1, 6)]
        for business, _, _ in businesses:
            target = dchoice(f"br-{business.name}", [2, 3, 4])
            existing = Review.objects.filter(business=business).count()
            for r in range(existing, target):
                rating, title, body = dchoice(
                    f"brs-{business.name}-{r}", REVIEW_SNIPPETS
                )
                u = reviewers[_h(f"bru-{business.name}-{r}") % len(reviewers)]
                Review.objects.create(
                    business=business,
                    rating=rating,
                    title=title,
                    body=body,
                    reviewer=u,
                    reviewer_name=u.get_full_name() or u.first_name,
                    is_verified_purchase=dchoice(
                        f"brv-{business.name}-{r}", [True, False]
                    ),
                )
        for variant in all_variants:
            if _h(f"vrev-{variant.sku}") % 3 != 0:  # ~1/3 of variants get reviews
                continue
            if variant.reviews.exists():
                continue
            for r in range(dchoice(f"vrn-{variant.sku}", [1, 2, 3])):
                rating, title, body = dchoice(f"vrs-{variant.sku}-{r}", REVIEW_SNIPPETS)
                u = reviewers[_h(f"vru-{variant.sku}-{r}") % len(reviewers)]
                Review.objects.create(
                    variant=variant,
                    rating=rating,
                    title=title,
                    body=body,
                    reviewer=u,
                    reviewer_name=u.get_full_name() or u.first_name,
                    is_verified_purchase=dchoice(
                        f"vrv-{variant.sku}-{r}", [True, False]
                    ),
                )
        self.stdout.write(f"Reviews: {Review.objects.count()}")

        # ── Sample order ──
        biz0 = businesses[0][0]
        if not MarketplaceOrder.objects.filter(business=biz0).exists():
            biz0_variants = [v for v in all_variants if v.item.business_id == biz0.id][
                :2
            ]
            if biz0_variants:
                order = MarketplaceOrder.objects.create(
                    business=biz0,
                    buyer_name="Selam Trading PLC",
                    buyer_email="buyer@selamtrading.test",
                    buyer_phone="912000111",
                    notes="Please confirm availability for delivery to Adama.",
                    status="PENDING",
                )
                total = Decimal("0")
                for v in biz0_variants:
                    qty = 25
                    price = Decimal(v.selling_price or 0)
                    total += price * qty
                    MarketplaceOrderItem.objects.create(
                        order=order, variant=v, quantity=qty, price=price
                    )
                order.total_payable = total
                order.save(update_fields=["total_payable", "updated_at"])

        # ── Waitlist samples ──
        for em, fn, bn in [
            ("merchant1@example.com", "Aster Bekele", "Aster Retail"),
            ("merchant2@example.com", "Kebede Stores", "Kebede Stores"),
        ]:
            Waitlist.objects.get_or_create(
                email=em, defaults={"full_name": fn, "business_name": bn}
            )

        self.stdout.write(self.style.SUCCESS("Marketplace seed complete."))

    # ── helpers ──
    def _owner(self, i, name):
        phone = f"9{10000000 + i:08d}"[:9]
        user = User.objects.filter(phone_number=phone).first()
        if not user:
            user = User.objects.create_user(
                phone_number=phone,
                email=f"owner{i}@bitamarket.test",
                password="bita1234",
                first_name=name.split()[0],
                last_name="Owner",
                is_phone_verified=True,
            )
        return user

    def _buyer(self, i):
        phone = f"7{20000000 + i:08d}"[:9]
        user = User.objects.filter(phone_number=phone).first()
        if not user:
            user = User.objects.create_user(
                phone_number=phone,
                email=f"buyer{i}@bitamarket.test",
                password="bita1234",
                first_name=FIRST_NAMES[i % len(FIRST_NAMES)],
                last_name=LAST_NAMES[i % len(LAST_NAMES)],
                is_phone_verified=True,
            )
        return user

    def _flush(self):
        names = [b[0] for b in BUSINESSES]
        biz_qs = Business.objects.filter(name__in=names)
        Review.objects.filter(variant__item__business__in=biz_qs).delete()
        Review.objects.filter(business__in=biz_qs).delete()
        MarketplaceOrder.objects.filter(business__in=biz_qs).delete()
        biz_qs.delete()  # cascades items, variants, pricing, properties, images
        Waitlist.objects.filter(email__endswith="@example.com").delete()
        FileMeta.objects.filter(key__startswith="seed/").delete()
        self.stdout.write("Flushed previously seeded demo data.")

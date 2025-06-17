from django.contrib.postgres.search import TrigramSimilarity
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
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
        business_id = self.request.query_params.get("business_id")

        name = self.request.query_params.get("name")

        if name:
            queryset = queryset.filter(name__icontains=name)
        if business_id:
            queryset = queryset.filter(business=business_id)
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
        business_id = self.request.query_params.get("business_id")
        name = self.request.query_params.get("name")

        price_from = self.request.query_params.get("price_from")
        price_to = self.request.query_params.get("price_to")
        batch_number = self.request.query_params.get("batch_number")
        sku = self.request.query_params.get("sku")
        expire_date_from = self.request.query_params.get("expire_date_from")
        expire_date_to = self.request.query_params.get("expire_date_to")
        man_date_from = self.request.query_params.get("man_date_from")
        man_date_to = self.request.query_params.get("man_date_to")

        if price_from:
            queryset = queryset.filter(selling_price__gte=price_from)
        if price_to:
            queryset = queryset.filter(selling_price__lte=price_to)
        if expire_date_from:
            queryset = queryset.filter(expire_date__gte=expire_date_from)
        if expire_date_to:
            queryset = queryset.filter(expire_date__lte=expire_date_to)
        if man_date_from:
            queryset = queryset.filter(man_date__gte=man_date_from)
        if man_date_to:
            queryset = queryset.filter(man_date__lte=man_date_to)
        if batch_number:
            queryset = queryset.filter(batch_number__icontains=batch_number)
        if sku:
            queryset = queryset.filter(sku__icontains=sku)

        if name:
            queryset = queryset.filter(name__icontains=name)

        if business_id:
            queryset = queryset.filter(item__business=business_id)

        if item_id:
            queryset = queryset.filter(item=item_id)
        return queryset


class InventoryMovementViewSet(ModelViewSet):
    """ViewSet for managing inventory movements between branches"""

    queryset = InventoryMovement.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return InventoryMovementCreateSerializer
        return InventoryMovementSerializer

    def get_queryset(self):
        queryset = self.queryset.select_related(
            "from_branch", "to_branch", "business", "requested_by"
        ).prefetch_related("movement_items__supplied_item__item")

        user = self.request.user
        business_id = self.request.query_params.get("business_id")
        branch_id = self.request.query_params.get("branch_id")
        status_filter = self.request.query_params.get("status")

        if business_id:
            queryset = queryset.filter(business_id=business_id)

        if branch_id:
            # Show movements where user's branch is either source or destination
            queryset = queryset.filter(
                models.Q(from_branch_id=branch_id) | models.Q(to_branch_id=branch_id)
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        return queryset

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a pending inventory movement"""
        movement = self.get_object()

        if movement.status != "pending":
            return Response(
                {"error": "Only pending movements can be approved"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            movement.status = "approved"
            movement.approved_by = request.user
            movement.approved_at = timezone.now()
            movement.save()

        serializer = self.get_serializer(movement)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        """Mark movement as shipped and reduce inventory from source"""
        movement = self.get_object()

        if movement.status != "approved":
            return Response(
                {"error": "Only approved movements can be shipped"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        shipped_items = request.data.get("items", [])

        with transaction.atomic():
            for item_data in shipped_items:
                movement_item = movement.movement_items.get(
                    id=item_data["movement_item_id"]
                )
                quantity_shipped = item_data["quantity_shipped"]

                if quantity_shipped > movement_item.quantity_requested:
                    return Response(
                        {
                            "error": f"Shipped quantity cannot exceed requested quantity for {movement_item.supplied_item.item.name}"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Update movement item
                movement_item.quantity_shipped = quantity_shipped
                movement_item.save()

                # Reduce inventory from source
                movement_item.supplied_item.quantity -= quantity_shipped
                movement_item.supplied_item.save()

            movement.status = "shipped"
            movement.shipped_by = request.user
            movement.shipped_at = timezone.now()
            movement.save()

        serializer = self.get_serializer(movement)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        """Mark movement as received and add inventory to destination"""
        movement = self.get_object()

        if movement.status != "shipped":
            return Response(
                {"error": "Only shipped movements can be received"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        received_items = request.data.get("items", [])

        with transaction.atomic():
            for item_data in received_items:
                movement_item = movement.movement_items.get(
                    id=item_data["movement_item_id"]
                )
                quantity_received = item_data["quantity_received"]

                if quantity_received > movement_item.quantity_shipped:
                    return Response(
                        {
                            "error": f"Received quantity cannot exceed shipped quantity for {movement_item.supplied_item.item.name}"
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Update movement item
                movement_item.quantity_received = quantity_received
                movement_item.save()

                # Add inventory to destination
                # First, try to find existing supply in destination branch
                destination_supply, created = Supply.objects.get_or_create(
                    branch=movement.to_branch,
                    label=movement_item.supplied_item.supply.label,
                )

                # Check if same item already exists in destination supply
                existing_supplied_item = SuppliedItem.objects.filter(
                    supply=destination_supply,
                    item=movement_item.supplied_item.item,
                    batch_number=movement_item.supplied_item.batch_number,
                    product_number=movement_item.supplied_item.product_number,
                ).first()

                if existing_supplied_item:
                    # Add to existing stock
                    existing_supplied_item.quantity += quantity_received
                    existing_supplied_item.save()
                else:
                    # Create new supplied item in destination
                    SuppliedItem.objects.create(
                        supply=destination_supply,
                        item=movement_item.supplied_item.item,
                        quantity=quantity_received,
                        purchase_price=movement_item.supplied_item.purchase_price,
                        batch_number=movement_item.supplied_item.batch_number,
                        product_number=f"{movement_item.supplied_item.product_number}-T{movement.id}",  # Avoid duplicate product numbers
                        expire_date=movement_item.supplied_item.expire_date,
                        man_date=movement_item.supplied_item.man_date,
                        business=movement.business,
                        supplier=movement_item.supplied_item.supplier,
                    )

            movement.status = "received"
            movement.received_by = request.user
            movement.received_at = timezone.now()
            movement.save()

        serializer = self.get_serializer(movement)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a movement (only if pending or approved)"""
        movement = self.get_object()

        if movement.status not in ["pending", "approved"]:
            return Response(
                {"error": "Only pending or approved movements can be cancelled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        movement.status = "cancelled"
        movement.save()

        serializer = self.get_serializer(movement)
        return Response(serializer.data)


class InventoryMovementItemViewSet(ModelViewSet):
    """ViewSet for individual movement items"""

    queryset = InventoryMovementItem.objects.all()
    serializer_class = InventoryMovementItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset.select_related("movement", "supplied_item__item")

        movement_id = self.request.query_params.get("movement_id")
        if movement_id:
            queryset = queryset.filter(movement_id=movement_id)

        return queryset

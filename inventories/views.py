from django.contrib.postgres.search import TrigramSimilarity
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from guardian.shortcuts import assign_perm, get_objects_for_user, get_perms, remove_perm
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import (
    CreateModelMixin,
    DestroyModelMixin,
    ListModelMixin,
    RetrieveModelMixin,
    UpdateModelMixin,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from business.models import AdditionalBusinessPermissionNames, Business
from business.permissions import (
    BranchLevelPermission,
    BusinessLevelPermission,
    GuardianObjectPermissions,
)

from .filters import GroupFilter, ItemFilter, ItemVariantFilter, SupplierFilter
from .models import *
from .serializers import *


class ItemViewset(ModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    permission_classes = [
        IsAuthenticated,
        GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
    ]
    filterset_class = ItemFilter

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_ITEM.value[0] + "_business",
            self.request.business,
        ):
            queryset = queryset.filter(business=self.request.business)
        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_ITEM.value[0] + "_branch",
            self.request.branch,
        ):
            queryset = queryset.filter(branch=self.request.branch)
        else:
            queryset = queryset.none()
        return queryset


class SupplyViewset(
    ListModelMixin, CreateModelMixin, RetrieveModelMixin, GenericViewSet
):
    serializer_class = SupplySerializer
    permission_classes = [
        IsAuthenticated,
        GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
    ]
    queryset = Supply.objects.all()

    def get_queryset(self):
        queryset = self.queryset
        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_SUPPLY.value[0] + "_business",
            self.request.business,
        ):
            queryset = queryset.filter(business=self.request.business)
        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_SUPPLY.value[0] + "_branch",
            self.request.branch,
        ):
            queryset = queryset.filter(branch=self.request.branch)
        else:
            queryset = queryset.none()
        return queryset.order_by("updated_at")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return SupplyDetailsSerializer
        return self.serializer_class


class SupplierViewset(ListModelMixin, CreateModelMixin, GenericViewSet):
    serializer_class = SupplierSerializer
    permission_classes = [
        IsAuthenticated,
        GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
    ]
    queryset = Supplier.objects.all()
    filterset_class = SupplierFilter

    def get_queryset(self):
        queryset = self.queryset
        return queryset.filter(business=self.request.business)


class SupplyItemViewset(CreateModelMixin, GenericViewSet):
    serializer_class = SuppliedItemSerializer
    permission_classes = [
        IsAuthenticated,
        GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
    ]
    queryset = SuppliedItem.objects.all()

    def get_queryset(self):
        queryset = self.queryset
        supply_id = self.request.query_params.get("supply_id")
        if supply_id:
            queryset = queryset.filter(supply=supply_id)
        return queryset


class PricingViewset(
    CreateModelMixin, DestroyModelMixin, UpdateModelMixin, GenericViewSet
):
    queryset = (
        ItemVariant.objects.all()
    )  # Leave here to check for variant permission checks on business and branch level
    serializer_class = PricingSerializer
    permission_classes = [
        IsAuthenticated,
        BusinessLevelPermission | BranchLevelPermission,
    ]

    def get_queryset(self):
        return Pricing.objects.all()


class GroupViewset(ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [
        IsAuthenticated,
        GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
    ]
    filterset_class = GroupFilter

    def get_queryset(self):
        queryset = self.queryset
        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_GROUP.value[0] + "_business",
            self.request.business,
        ):
            queryset = queryset.filter(business=self.request.business)
        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_GROUP.value[0] + "_branch",
            self.request.branch,
        ):
            queryset = queryset.filter(branch=self.request.branch)
        else:
            queryset = queryset.none()
        return queryset


class ItemVariantViewset(ModelViewSet):
    queryset = ItemVariant.objects.all()
    serializer_class = ItemVariantSerializer
    permission_classes = [
        IsAuthenticated,
        GuardianObjectPermissions | BusinessLevelPermission | BranchLevelPermission,
    ]
    filterset_class = ItemVariantFilter

    def get_queryset(self):
        queryset = self.queryset
        item = self.request.query_params.get("item")
        if item:
            queryset = queryset.filter(item=item)

        if self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_ITEM_VARIANT.value[0]
            + "_business",
            self.request.business,
        ):
            queryset = queryset.filter(item__business=self.request.business)
        elif self.request.user.has_perm(
            AdditionalBusinessPermissionNames.CAN_VIEW_ITEM_VARIANT.value[0]
            + "_branch",
            self.request.branch,
        ):
            queryset = queryset.filter(branch=self.request.branch)
        else:
            queryset = queryset.none()

        return queryset


class PropertyViewset(
    CreateModelMixin, DestroyModelMixin, UpdateModelMixin, GenericViewSet
):
    queryset = (
        ItemVariant.objects.all()
    )  # Leave here to check for variant permission checks on business and branch level
    serializer_class = PropertySerializer
    permission_classes = [
        IsAuthenticated,
        BusinessLevelPermission | BranchLevelPermission,
    ]

    def get_queryset(self):
        return Property.objects.all()


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
                        selling_price=movement_item.supplied_item.selling_price,
                        purchase_price=movement_item.supplied_item.purchase_price,
                        batch_number=movement_item.supplied_item.batch_number,
                        product_number=f"{movement_item.supplied_item.product_number}-T{movement.id}",  # Avoid duplicate product numbers
                        expire_date=movement_item.supplied_item.expire_date,
                        man_date=movement_item.supplied_item.man_date,
                        business=movement.business,
                        variant=movement_item.variant,
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

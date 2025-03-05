from rest_framework import status, viewsets
from rest_framework.response import Response

from .models import SuppliedItem, Supply
from .serializers import SuppliedItemSerializer, SupplySerializer


class SupplyViewSetV1(viewsets.ModelViewSet):
    queryset = Supply.objects.all()
    serializer_class = SupplySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        supplied_items_data = request.data.get("supplied_items", [])
        for item_data in supplied_items_data:
            SuppliedItem.objects.create(supply=serializer.instance, **item_data)

        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class SuppliedItemViewSetV1(viewsets.ModelViewSet):
    queryset = SuppliedItem.objects.all()
    serializer_class = SuppliedItemSerializer

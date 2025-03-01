from rest_framework import viewsets
from .models import Supply, SuppliedItem
from .serializers import SupplySerializer, SuppliedItemSerializer

class SupplyViewSetV1(viewsets.ModelViewSet):
    queryset = Supply.objects.all()
    serializer_class = SupplySerializer

class SuppliedItemViewSetV1(viewsets.ModelViewSet):
    queryset = SuppliedItem.objects.all()
    serializer_class = SuppliedItemSerializer
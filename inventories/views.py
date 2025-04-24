from django.contrib.postgres.search import TrigramSimilarity
from rest_framework import viewsets

from .models import Item
from .serializers import ItemSerializer


class ItemViewSet(viewsets.ModelViewSet):
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

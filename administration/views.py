from rest_framework import mixins, viewsets

from .models import FAQ, Contact, Download, Plan, Waitlist
from .serializers import (
    ContactSerializer,
    DownloadSerializer,
    FAQSerializer,
    PlanSerializer,
    WaitlistSerializer,
)


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    pagination_class = None


class DownloadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Download.objects.all()
    serializer_class = DownloadSerializer
    pagination_class = None


class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    pagination_class = None


class WaitlistViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Waitlist.objects.all()
    serializer_class = WaitlistSerializer


class ContactViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer

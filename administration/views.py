from rest_framework import mixins, status, viewsets
from rest_framework.response import Response

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


class DownloadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Download.objects.all()
    serializer_class = DownloadSerializer


class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer


class WaitlistViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Waitlist.objects.all()
    serializer_class = WaitlistSerializer


class ContactViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer

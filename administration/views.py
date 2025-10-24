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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(
            {**serializer.data, "message": "added to waitlist"},
            status=status.HTTP_201_CREATED,
            headers=headers,
        )


class ContactViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()
        headers = self.get_success_headers(serializer.data)
        return Response(
            {
                "id": contact.id,
                "received_at": contact.received_at,
                "message": "Your message has been received. We will contact you soon.",
            },
            status=status.HTTP_201_CREATED,
            headers=headers,
        )

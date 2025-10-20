from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Plan, Download, Waitlist, FAQ, Contact
from .serializers import (
    PlanSerializer,
    DownloadSerializer,
    WaitlistSerializer,
    FAQSerializer,
    ContactSerializer,
)
from django.shortcuts import get_object_or_404


class PlanView(APIView):

    def get(self, request, pk=None):
        if pk:
            plan = get_object_or_404(Plan, pk=pk)
            serializer = PlanSerializer(plan)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            plans = Plan.objects.all()
            serializer = PlanSerializer(plans, many=True)
            return Response({"plans": serializer.data}, status=status.HTTP_200_OK)


class DownloadView(APIView):

    def get(self, request, pk=None):
        if pk:
            download = get_object_or_404(Download, pk=pk)
            serializer = DownloadSerializer(download)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            downloads = Download.objects.all()
            serializer = DownloadSerializer(downloads, many=True)
            return Response({"downloads": serializer.data}, status=status.HTTP_200_OK)


class WaitlistView(APIView):
    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        if Waitlist.objects.filter(email=email).exists():
            return Response(
                {"email": ["This email is already in the waitlist."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = WaitlistSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            response_data = serializer.data
            response_data["message"] = "added to waitlist"
            return Response(response_data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FAQView(APIView):

    def get(self, request, pk=None):
        if pk:
            faq = get_object_or_404(FAQ, pk=pk)
            serializer = FAQSerializer(faq)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            faqs = FAQ.objects.all()
            serializer = FAQSerializer(faqs, many=True)
            return Response({"faqs": serializer.data}, status=status.HTTP_200_OK)


class ContactView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = ContactSerializer(data=request.data)
        if serializer.is_valid():
            contact = serializer.save()
            return Response(
                {
                    "id": contact.id,
                    "received_at": contact.received_at,
                    "message": "Your message has been received. We will contact you soon.",
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

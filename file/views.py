import os

from django.http import FileResponse
from django.shortcuts import get_object_or_404, render
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from .models import FileModel
from .serializers import FileDownloadSerializer, FileUploadSerializer
from .spectacular_schemas import file_download_schema, file_upload_schema


class UploadViewSet(ViewSet):
    serializer_class = FileUploadSerializer
    parser_classes = [MultiPartParser, FormParser]

    @file_upload_schema
    def create(self, request):
        my_file = FileUploadSerializer(data=request.data)
        if my_file.is_valid():
            saved_file = my_file.save()
            response = {
                "message": "File uploaded successfully",
                "stored_as": saved_file.stored_as,
            }
        else:
            response = {"message": "Invalid request", "errors": my_file.errors}

        return Response(response)


class FileDownloadView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    @file_download_schema
    def get(self, request, stored_as):

        file_instance = get_object_or_404(FileModel, stored_as=stored_as)

        response_data = FileDownloadSerializer(file_instance).data
        return Response(response_data)

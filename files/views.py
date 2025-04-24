import os
from uuid import uuid4

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from files.serializers import *


class SignUrlViewset(CreateModelMixin, GenericViewSet):
    serializer_class = SignedURLSerializer
    permission_classes = [IsAuthenticated]


class FileMetaDataViewset(
    CreateModelMixin, ListModelMixin, DestroyModelMixin, GenericViewSet
):
    serializer_class = FileMetaSerializer
    permission_classes = [IsAuthenticated]

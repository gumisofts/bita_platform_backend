import io
import logging
import os
from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import models
from PIL import Image
from storages.backends.s3boto3 import S3Boto3Storage

from core.models import BaseModel

logger = logging.getLogger(__name__)


class FileMeta(models.Model):
    key = models.CharField(max_length=255, primary_key=True)
    public_url = models.CharField(max_length=255)

class FilePurpose(models.TextChoices):
    PROFILE_PICTURE = "PROFILE_PICTURE"
    ITEM = "ITEM"
    RECEIPT = "RECEIPT"
    CHAT = "CHAT"
    REPORT = "REPORT"
    INVOICE = "INVOICE"
    OTHER = "OTHER"

class FileModel(BaseModel):
    
    def upload_to(self, filename):
        return f"{self.purpose.lower()}/{filename}"
    
    file = models.FileField(upload_to=upload_to)
    purpose = models.CharField(max_length=255, choices=FilePurpose.choices)

    def __str__(self):
        return self.file.name
    
    def get_file_url(self):
        return self.file.url
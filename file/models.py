import io
import logging
import os
from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import models
from PIL import Image
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)


class FileModel(models.Model):
    stored_as = models.CharField(
        primary_key=True, max_length=255, unique=True, blank=True, default=uuid4
    )

    name = models.CharField(max_length=255)

    # Store the original file
    file = models.FileField(storage=S3Boto3Storage(), null=True, blank=True)

    # Store different versions for images only
    optimized_image = models.ImageField(storage=S3Boto3Storage(), null=True, blank=True)
    thumbnail = models.ImageField(storage=S3Boto3Storage(), null=True, blank=True)

    file_type = models.CharField(max_length=50, blank=True)
    file_size = models.PositiveBigIntegerField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_retrieved_at = models.DateTimeField(null=True, blank=True)
    alt_text = models.TextField()
    retrieval_count = models.PositiveIntegerField(default=0)
    file_extension = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):

        # Set file size before saving
        if self.file:
            # get extension
            self.file_extension = os.path.splitext(self.file.name)[1].lower()
            # build filename
            original_filename = f"{self.stored_as}{self.file_extension}"
            # set file name and size
            self.file.name = original_filename
            self.file_size = self.file.size
            print(self.file.name)

        super().save(*args, **kwargs)  # Save the original file first!

        # Generate optimized versions *AFTER* the file is saved
        if self.file_extension in [".png", ".jpg", ".jpeg", ".gif"]:
            self.generate_image_versions()
            super().save(
                update_fields=["optimized_image", "thumbnail"]
            )  # Save only these fields

    def generate_image_versions(self):

        with self.file.open("rb") as f:
            img = Image.open(f)

        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background
            # pallete image alpha extraction
        elif img.mode == "P":
            img = img.convert("RGB")
            background = Image.new("RGB", img.size, (255, 255, 255))
            alpha = img.split()[-1] if img.mode == "RGBA" else None
            if alpha:
                background.paste(img, mask=alpha)

        # Resize for optimized version
        optimized = img.copy()
        optimized.thumbnail((800, 800), Image.Resampling.LANCZOS)

        # Resize for thumbnail version
        thumbnail = img.copy()
        thumbnail.thumbnail((200, 200), Image.Resampling.LANCZOS)

        # Generate filenames dynamically
        optimized_filename = f"{self.stored_as}_optimized{self.file_extension}"
        thumbnail_filename = f"{self.stored_as}_thumbnail{self.file_extension}"

        # Save optimized image to memory
        optimized_io = io.BytesIO()
        optimized.save(optimized_io, format="JPEG", quality=85)
        optimized_file = ContentFile(optimized_io.getvalue(), name=optimized_filename)

        # Save thumbnail to memory
        thumbnail_io = io.BytesIO()
        thumbnail.save(thumbnail_io, format="JPEG", quality=75)
        thumbnail_file = ContentFile(thumbnail_io.getvalue(), name=thumbnail_filename)
        print(thumbnail_filename, optimized_filename)
        # Assign to fields and save
        self.optimized_image.save(optimized_filename, optimized_file, save=False)
        self.thumbnail.save(thumbnail_filename, thumbnail_file, save=False)

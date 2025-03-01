import logging
import os
import uuid
from io import BytesIO

from django.db import models
from django.utils.timezone import now
from storages.backends.s3boto3 import S3Boto3Storage

logger = logging.getLogger(__name__)


def file_upload_to(instance, filename):
    logger.info(f"Processing field: for file: {filename}")
    file_extension = filename.split(".")[-1].lower()
    file_folder = {
        "png": "images/",
        "jpg": "images/",
        "jpeg": "images/",
        "gif": "images/",
        "mp3": "audio/",
        "mp4": "video/",
        "pdf": "documents/",
    }.get(file_extension, "others/")
    # Generate a unique filename for each version of the image
    if hasattr(instance, "optimized_image") and instance.optimized_image:
        return os.path.join(
            file_folder, f"{instance.stored_as}_optimized.{file_extension}"
        )
    elif hasattr(instance, "thumbnail") and instance.thumbnail:
        return os.path.join(
            file_folder, f"{instance.stored_as}_thumbnail.{file_extension}"
        )
    else:
        return os.path.join(file_folder, f"xcx{instance.stored_as}.{file_extension}")


class FileModel(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    stored_as = models.CharField(max_length=255, unique=True, blank=True, null=True)

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

    # def __str__(self):
    #     return self.name

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.stored_as:
            self.stored_as = uuid.uuid4().hex  # Generate a unique ID
            # self.file_extension = os.path.splitext(self.file.name)[1].lower()  # Extract file extension
            self.file_extension = os.path.splitext(self.file.name)[
                1
            ].lower()  # Extract file extension
        # Set file size before saving
        if self.file:
            original_filename = f"{self.stored_as}{self.file_extension}"
            self.file.name = original_filename  # Set the new filename
            self.file_size = self.file.size  # Set file size

        super().save(*args, **kwargs)  # Save the original file first!

        # Generate optimized versions *AFTER* the file is saved
        if self.file_extension in [".png", ".jpg", ".jpeg", ".gif"]:
            self.generate_image_versions()
            super().save(
                update_fields=["optimized_image", "thumbnail"]
            )  # Save only these fields

    def generate_image_versions(self):
        import io

        import requests
        from django.core.files.base import ContentFile
        from PIL import Image

        # Read the image from S3
        response = requests.get(self.file.url, stream=True)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))

        if img.mode in ("RGBA", "LA"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[-1])
            img = background

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

        # Assign to fields and save
        self.optimized_image.save(optimized_filename, optimized_file, save=False)
        self.thumbnail.save(thumbnail_filename, thumbnail_file, save=False)

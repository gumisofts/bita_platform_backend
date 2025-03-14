from rest_framework import serializers
from rest_framework.serializers import FileField, ModelSerializer

from .models import FileModel


class FileDownloadSerializer(serializers.Serializer):
    message = serializers.CharField(default="File retrieved successfully")
    file_url = serializers.SerializerMethodField()
    optimized_image_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    alt_text = serializers.CharField(required=False)
    error = serializers.CharField(required=False)

    def get_file_url(self, obj):
        """Returns the original file URL"""
        if hasattr(obj, "file") and obj.file:
            return obj.file.url  # Original file
        return None

    def get_optimized_image_url(self, obj):
        """Returns the optimized image URL if available"""
        if hasattr(obj, "optimized_image") and obj.optimized_image:
            return obj.optimized_image.url  # Optimized version
        return None

    def get_thumbnail_url(self, obj):
        """Returns the thumbnail URL if available"""
        if hasattr(obj, "thumbnail") and obj.thumbnail:
            return obj.thumbnail.url  # Thumbnail version
        return None


class FileUploadSerializer(ModelSerializer):
    file = FileField()

    class Meta:
        model = FileModel
        fields = ["file", "alt_text"]
        read_only_fields = ["stored_as"]


class FileMetadataSerializer(serializers.Serializer):
    file_name = serializers.CharField()
    file_size = serializers.IntegerField()
    alt_text = serializers.CharField(required=False, allow_blank=True)

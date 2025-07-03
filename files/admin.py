from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from files.models import FileMeta


@admin.register(FileMeta)
class FileMetaAdmin(admin.ModelAdmin):
    list_display = [
        "key",
        "file_size_display",
        "file_type",
        "url_preview",
        "public_url",
    ]
    search_fields = ["key", "public_url"]
    readonly_fields = ["file_preview", "full_url"]

    fieldsets = (
        (None, {"fields": ("key", "public_url")}),
        (_("File Information"), {"fields": ("file_preview", "full_url")}),
    )

    def url_preview(self, obj):
        url = self.get_full_url(obj)
        return format_html('<a href="{}" target="_blank">View File</a>', url)

    url_preview.short_description = "Preview"

    def full_url(self, obj):
        url = self.get_full_url(obj)
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)

    full_url.short_description = "Full URL"

    def file_preview(self, obj):
        url = self.get_full_url(obj)
        file_extension = obj.key.split(".")[-1].lower() if "." in obj.key else ""

        # Image preview
        if file_extension in ["jpg", "jpeg", "png", "gif", "webp", "svg"]:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px; object-fit: contain;" />',
                url,
            )
        # Video preview
        elif file_extension in ["mp4", "webm", "ogg"]:
            return format_html(
                '<video controls style="max-width: 200px; max-height: 200px;"><source src="{}" type="video/{}"></video>',
                url,
                file_extension,
            )
        # Audio preview
        elif file_extension in ["mp3", "wav", "ogg"]:
            return format_html(
                '<audio controls><source src="{}" type="audio/{}"></audio>',
                url,
                file_extension,
            )
        # PDF preview
        elif file_extension == "pdf":
            return format_html(
                '<embed src="{}" type="application/pdf" width="200" height="200" />',
                url,
            )
        # Default file icon
        else:
            return format_html(
                '<div style="padding: 20px; border: 1px solid #ccc; text-align: center; width: 200px;">'
                "<strong>📄</strong><br>{}</div>",
                file_extension.upper() if file_extension else "FILE",
            )

    file_preview.short_description = "Preview"

    def file_type(self, obj):
        file_extension = obj.key.split(".")[-1].lower() if "." in obj.key else "unknown"

        # Categorize file types
        image_types = ["jpg", "jpeg", "png", "gif", "webp", "svg"]
        video_types = ["mp4", "webm", "ogg", "avi", "mov"]
        audio_types = ["mp3", "wav", "ogg", "flac"]
        document_types = ["pdf", "doc", "docx", "txt", "rtf"]

        if file_extension in image_types:
            icon = "🖼️"
            category = "Image"
        elif file_extension in video_types:
            icon = "🎥"
            category = "Video"
        elif file_extension in audio_types:
            icon = "🎵"
            category = "Audio"
        elif file_extension in document_types:
            icon = "📄"
            category = "Document"
        else:
            icon = "📁"
            category = "File"

        return f"{icon} {category} (.{file_extension})"

    file_type.short_description = "Type"

    def file_size_display(self, obj):
        # This would require adding a size field to the model
        # For now, we'll show a placeholder
        return "N/A"

    file_size_display.short_description = "Size"

    def get_full_url(self, obj):
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        region = settings.AWS_S3_REGION_NAME
        return f"https://{bucket}.s3.{region}.amazonaws.com/{obj.key}"

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("key")


# Custom admin actions
@admin.action(description="Generate download links for selected files")
def generate_download_links(modeladmin, request, queryset):
    from django.contrib import messages

    links = []
    for file_meta in queryset:
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        region = settings.AWS_S3_REGION_NAME
        url = f"https://{bucket}.s3.{region}.amazonaws.com/{file_meta.key}"
        links.append(f"• {file_meta.key}: {url}")

    message = "Download links:\n" + "\n".join(links)
    messages.success(request, message)


@admin.action(description="Check file accessibility")
def check_file_accessibility(modeladmin, request, queryset):
    import requests
    from django.contrib import messages

    accessible = 0
    inaccessible = 0

    for file_meta in queryset:
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        region = settings.AWS_S3_REGION_NAME
        url = f"https://{bucket}.s3.{region}.amazonaws.com/{file_meta.key}"

        try:
            response = requests.head(url, timeout=5)
            if response.status_code == 200:
                accessible += 1
            else:
                inaccessible += 1
        except:
            inaccessible += 1

    messages.info(
        request,
        f"File accessibility check: {accessible} accessible, {inaccessible} inaccessible",
    )


# Add actions to FileMetaAdmin
FileMetaAdmin.actions = [generate_download_links, check_file_accessibility]

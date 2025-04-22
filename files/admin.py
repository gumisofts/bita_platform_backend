from django.contrib import admin
from files.models import FileMeta
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.conf import settings


class FileMetaAdmin(admin.ModelAdmin):
    list_display = ["key", "url"]

    def url(self, instance):
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        region = settings.AWS_S3_REGION_NAME

        url = f"https://{bucket}.s3.{region}.amazonaws.com/{instance.key}"
        return mark_safe(f"<a href={url}>{url}</a>")


admin.site.register(FileMeta, FileMetaAdmin)

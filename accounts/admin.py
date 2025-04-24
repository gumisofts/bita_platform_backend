from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import *


class CustomUserAdmin(UserAdmin):
    list_display = (
        "id",
        "email",
        "phone_number",
        "first_name",
        "last_name",
        "is_phone_verified",
        "is_email_verified",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_staff", "is_active")
    ordering = ("date_joined",)


class ResetRequestAdmin(admin.ModelAdmin):
    list_display = ["email", "phone_number", "user", "code"]


class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "phone_number", "user", "is_used"]

    ordering = ["created_at"]


class PermissionAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "codename", "content_type"]
    ordering = ["id"]
    list_filter = []


class ContentTypeAdmin(admin.ModelAdmin):
    list_display = ["id", "model", "app_label"]
    ordering = ["id"]
    list_filter = ["app_label"]
    list_select_related = []


admin.site.register(VerificationCode, VerificationCodeAdmin)
admin.site.register(Permission, PermissionAdmin)
admin.site.register(ContentType, ContentTypeAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(ResetPasswordRequest, ResetRequestAdmin)

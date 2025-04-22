from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import *

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html


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


class AddressAdmin(admin.ModelAdmin):
    list_display = ["lat", "lng", "admin_1", "country"]
    list_filter = ["country"]


class BusinessAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "business_type", "created_at", "updated_at"]
    list_filter = ["created_at"]


class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at", "updated_at"]


class ResetRequestAdmin(admin.ModelAdmin):
    list_display = ["email", "phone_number", "user", "code"]


class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ["id", "email", "phone_number", "user", "is_used"]

    ordering = ["created_at"]


class IndustryAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    ordering = []


class PermissionAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "codename", "content_type"]
    ordering = ["id"]
    list_filter = []


class ContentTypeAdmin(admin.ModelAdmin):
    list_display = ["id", "model", "app_label"]
    ordering = ["id"]
    list_filter = ["app_label"]
    list_select_related = []


class RoleAdmin(admin.ModelAdmin):
    list_display = ["id", "role_name", "business"]
    ordering = ["id"]
    list_filter = ["business"]
    list_select_related = []


admin.site.register(VerificationCode, VerificationCodeAdmin)
admin.site.register(Permission, PermissionAdmin)
admin.site.register(ContentType, ContentTypeAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Industry, IndustryAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Business, BusinessAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(ResetPasswordRequest, ResetRequestAdmin)

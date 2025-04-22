from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

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


admin.site.register(VerificationCode, VerificationCodeAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Business, BusinessAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(ResetPasswordRequest, ResetRequestAdmin)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import *


class UserDeviceInline(admin.TabularInline):
    model = UserDevice
    extra = 0
    readonly_fields = ("created_at", "updated_at")


class VerificationCodeInline(admin.TabularInline):
    model = VerificationCode
    extra = 0
    readonly_fields = ("created_at", "expires_at", "is_used")
    can_delete = False


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    list_display = (
        "id",
        "email",
        "phone_number",
        "full_name",
        "verification_status",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = (
        "is_staff",
        "is_active",
        "is_superuser",
        "is_email_verified",
        "is_phone_verified",
        "date_joined",
    )
    search_fields = ("email", "phone_number", "first_name", "last_name")
    ordering = ("-date_joined",)
    readonly_fields = ("id", "last_login", "date_joined", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("id", "password")}),
        (
            _("Personal info"),
            {"fields": ("first_name", "last_name", "email", "phone_number")},
        ),
        (
            _("Verification"),
            {
                "fields": ("is_email_verified", "is_phone_verified"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Important dates"),
            {
                "fields": ("last_login", "date_joined", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "phone_number",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    inlines = [UserDeviceInline, VerificationCodeInline]

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    full_name.short_description = "Full Name"

    def verification_status(self, obj):
        email_status = "✓" if obj.is_email_verified else "✗"
        phone_status = "✓" if obj.is_phone_verified else "✗"
        return format_html(f"Email: {email_status} | Phone: {phone_status}")

    verification_status.short_description = "Verification Status"
    
    def verify_phone_selected_users(self, request, queryset):
        for user in queryset:
            user.is_phone_verified = True
            user.save()
        self.message_user(request, "Selected users have been verified")

    verify_phone_selected_users.short_description = "Verify Phone"
    
    actions = [verify_phone_selected_users]


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    list_display = ["id", "user_email", "label", "fcm_token_short", "created_at"]
    list_filter = ["created_at", "label"]
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "label",
        "fcm_token",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["user"]

    fieldsets = (
        (None, {"fields": ("id", "user", "label", "fcm_token")}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def user_email(self, obj):
        return obj.user.email if obj.user else "-"

    user_email.short_description = "User Email"

    def fcm_token_short(self, obj):
        return f"{obj.fcm_token[:20]}..." if len(obj.fcm_token) > 20 else obj.fcm_token

    fcm_token_short.short_description = "FCM Token"


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "user_info",
        "contact_method",
        "is_used",
        "expires_at",
        "created_at",
    ]
    list_filter = ["is_used", "expires_at", "created_at"]
    search_fields = [
        "user__email",
        "user__phone_number",
        "email",
        "phone_number",
        "code",
    ]
    readonly_fields = ["id", "code", "created_at", "expires_at"]
    raw_id_fields = ["user"]

    fieldsets = (
        (None, {"fields": ("id", "user", "code", "is_used")}),
        (_("Contact Information"), {"fields": ("email", "phone_number")}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "expires_at"), "classes": ("collapse",)},
        ),
    )

    def user_info(self, obj):
        if obj.user:
            return f"{obj.user.email or obj.user.phone_number}"
        return "-"

    user_info.short_description = "User"

    def contact_method(self, obj):
        if obj.email:
            return f"Email: {obj.email}"
        elif obj.phone_number:
            return f"Phone: {obj.phone_number}"
        return "-"

    contact_method.short_description = "Contact Method"


@admin.register(ResetPasswordRequest)
class ResetPasswordRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "user_info", "contact_method", "is_used", "created_at"]
    list_filter = ["is_used", "created_at"]
    search_fields = ["user__email", "user__phone_number", "email", "phone_number"]
    readonly_fields = ["id", "code", "created_at"]
    raw_id_fields = ["user"]

    fieldsets = (
        (None, {"fields": ("id", "user", "code", "is_used")}),
        (_("Contact Information"), {"fields": ("email", "phone_number")}),
        (_("Timestamps"), {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    def user_info(self, obj):
        if obj.user:
            return f"{obj.user.email or obj.user.phone_number}"
        return "-"

    user_info.short_description = "User"

    def contact_method(self, obj):
        if obj.email:
            return f"Email: {obj.email}"
        elif obj.phone_number:
            return f"Phone: {obj.phone_number}"
        return "-"

    contact_method.short_description = "Contact Method"


@admin.register(EmailChangeRequest)
class EmailChangeRequestAdmin(admin.ModelAdmin):
    list_display = ["id", "user_email", "new_email", "created_at", "expires_at"]
    list_filter = ["created_at", "expires_at"]
    search_fields = ["user__email", "new_email"]
    readonly_fields = ["id", "created_at"]
    raw_id_fields = ["user"]

    def user_email(self, obj):
        return obj.user.email if obj.user else "-"

    user_email.short_description = "Current Email"


@admin.register(Password)
class PasswordAdmin(admin.ModelAdmin):
    list_display = ["id", "user_email", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["user__email", "user__phone_number"]
    readonly_fields = ["id", "password", "created_at"]
    raw_id_fields = ["user"]

    def user_email(self, obj):
        return obj.user.email if obj.user else "-"

    user_email.short_description = "User Email"


# Enhanced Permission and ContentType admins
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "codename", "content_type", "app_label"]
    list_filter = ["content_type__app_label"]
    search_fields = ["name", "codename", "content_type__model"]
    ordering = ["content_type__app_label", "codename"]

    def app_label(self, obj):
        return obj.content_type.app_label

    app_label.short_description = "App"


@admin.register(ContentType)
class ContentTypeAdmin(admin.ModelAdmin):
    list_display = ["id", "app_label", "model"]
    list_filter = ["app_label"]
    search_fields = ["app_label", "model"]
    ordering = ["app_label", "model"]

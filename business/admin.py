from django.contrib import admin

from business.models import *


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


class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "business", "role", "branch"]
    # ordering = ["created_at"]


class BranchAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "address", "business"]
    ordering = ["created_at"]


class AddressAdmin(admin.ModelAdmin):
    list_display = ["lat", "lng", "admin_1", "country"]
    list_filter = ["country"]


class BusinessAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "business_type", "created_at", "updated_at"]
    list_filter = ["created_at"]


class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at", "updated_at"]


class IndustryAdmin(admin.ModelAdmin):
    list_display = ["name", "created_at"]
    ordering = []


class EmployeeInvitationAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "email",
        "phone_number",
        "role",
        "branch",
        "business",
        "status",
    ]
    ordering = []


admin.site.register(Employee, EmployeeAdmin)
admin.site.register(Industry, IndustryAdmin)
admin.site.register(Address, AddressAdmin)
admin.site.register(Business, BusinessAdmin)
admin.site.register(Branch, BranchAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(EmployeeInvitation, EmployeeInvitationAdmin)

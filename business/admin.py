from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from business.models import *


class CategoryInline(admin.TabularInline):
    model = Category
    extra = 0
    fields = ('name', 'is_active')


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "is_active", "category_count", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [CategoryInline]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'is_active')
        }),
        (_('Media'), {
            'fields': ('image',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def category_count(self, obj):
        count = obj.category_set.count()
        return f"{count} categories"
    category_count.short_description = "Categories"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "industry_name", "is_active", "business_count", "created_at"]
    list_filter = ["is_active", "industry", "created_at"]
    search_fields = ["name", "industry__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["industry"]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'industry', 'is_active')
        }),
        (_('Media'), {
            'fields': ('image',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def industry_name(self, obj):
        return obj.industry.name if obj.industry else "-"
    industry_name.short_description = "Industry"
    
    def business_count(self, obj):
        count = obj.businesses.count()
        return f"{count} businesses"
    business_count.short_description = "Businesses"


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["id", "location_display", "full_address", "country", "created_at"]
    list_filter = ["country", "admin_1", "created_at"]
    search_fields = ["admin_1", "locality", "sublocality", "country", "plus_code"]
    readonly_fields = ["id", "created_at", "updated_at"]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'lat', 'lng', 'plus_code')
        }),
        (_('Address Details'), {
            'fields': ('sublocality', 'locality', 'admin_2', 'admin_1', 'country')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def location_display(self, obj):
        return f"{obj.lat:.4f}, {obj.lng:.4f}"
    location_display.short_description = "Coordinates"
    
    def full_address(self, obj):
        parts = [obj.sublocality, obj.locality, obj.admin_1]
        return ", ".join([part for part in parts if part])
    full_address.short_description = "Address"


class RoleInline(admin.TabularInline):
    model = Role
    extra = 0
    fields = ('role_name', 'permissions')
    filter_horizontal = ('permissions',)


class EmployeeInline(admin.TabularInline):
    model = Employee
    extra = 0
    fields = ('user', 'role', 'branch')
    raw_id_fields = ('user', 'role', 'branch')


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    fields = ('name', 'address')
    raw_id_fields = ('address',)


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "business_type", "owner_info", "employee_count", "branch_count", "created_at"]
    list_filter = ["business_type", "created_at"]
    search_fields = ["name", "owner__email", "owner__first_name", "owner__last_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["owner", "address"]
    filter_horizontal = ["categories"]
    inlines = [BranchInline, RoleInline, EmployeeInline]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'business_type', 'owner')
        }),
        (_('Location & Categories'), {
            'fields': ('address', 'categories')
        }),
        (_('Media'), {
            'fields': ('background_image',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def owner_info(self, obj):
        if obj.owner:
            return f"{obj.owner.email} ({obj.owner.first_name} {obj.owner.last_name})"
        return "-"
    owner_info.short_description = "Owner"
    
    def employee_count(self, obj):
        count = obj.employees.count()
        return f"{count} employees"
    employee_count.short_description = "Employees"
    
    def branch_count(self, obj):
        count = obj.branches.count()
        return f"{count} branches"
    branch_count.short_description = "Branches"


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["id", "role_name", "business_name", "permission_count", "employee_count"]
    list_filter = ["business", "created_at"]
    search_fields = ["role_name", "business__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["business"]
    filter_horizontal = ["permissions"]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'role_name', 'business')
        }),
        (_('Permissions'), {
            'fields': ('permissions',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def business_name(self, obj):
        return obj.business.name if obj.business else "-"
    business_name.short_description = "Business"
    
    def permission_count(self, obj):
        count = obj.permissions.count()
        return f"{count} permissions"
    permission_count.short_description = "Permissions"
    
    def employee_count(self, obj):
        count = obj.employees.count()
        return f"{count} employees"
    employee_count.short_description = "Employees"


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ["id", "user_info", "business_name", "role_name", "branch_name", "created_at"]
    list_filter = ["business", "role", "branch", "created_at"]
    search_fields = ["user__email", "user__first_name", "user__last_name", "business__name", "role__role_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["user", "business", "role", "branch"]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'user', 'business')
        }),
        (_('Position'), {
            'fields': ('role', 'branch')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_info(self, obj):
        if obj.user:
            return f"{obj.user.email} ({obj.user.first_name} {obj.user.last_name})"
        return "-"
    user_info.short_description = "User"
    
    def business_name(self, obj):
        return obj.business.name if obj.business else "-"
    business_name.short_description = "Business"
    
    def role_name(self, obj):
        return obj.role.role_name if obj.role else "-"
    role_name.short_description = "Role"
    
    def branch_name(self, obj):
        return obj.branch.name if obj.branch else "-"
    branch_name.short_description = "Branch"


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "business_name", "address_info", "employee_count", "created_at"]
    list_filter = ["business", "created_at"]
    search_fields = ["name", "business__name", "address__admin_1", "address__locality"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["business", "address"]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'name', 'business', 'address')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def business_name(self, obj):
        return obj.business.name if obj.business else "-"
    business_name.short_description = "Business"
    
    def address_info(self, obj):
        if obj.address:
            return f"{obj.address.locality}, {obj.address.admin_1}"
        return "-"
    address_info.short_description = "Location"
    
    def employee_count(self, obj):
        count = obj.employees.count()
        return f"{count} employees"
    employee_count.short_description = "Employees"


@admin.register(EmployeeInvitation)
class EmployeeInvitationAdmin(admin.ModelAdmin):
    list_display = ["id", "contact_info", "business_name", "role_name", "status", "created_at"]
    list_filter = ["status", "business", "role", "created_at"]
    search_fields = ["email", "phone_number", "business__name", "role__role_name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["business", "role", "branch"]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'business', 'status')
        }),
        (_('Contact Information'), {
            'fields': ('email', 'phone_number')
        }),
        (_('Position'), {
            'fields': ('role', 'branch')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def contact_info(self, obj):
        contact = obj.email or obj.phone_number or "-"
        return contact
    contact_info.short_description = "Contact"
    
    def business_name(self, obj):
        return obj.business.name if obj.business else "-"
    business_name.short_description = "Business"
    
    def role_name(self, obj):
        return obj.role.role_name if obj.role else "-"
    role_name.short_description = "Role"


@admin.register(BusinessActivity)
class BusinessActivityAdmin(admin.ModelAdmin):
    list_display = ["id", "action_display", "model_display", "employee_info", "business_name", "timestamp"]
    list_filter = ["action", "model", "business", "timestamp"]
    search_fields = ["employee__user__email", "business__name"]
    readonly_fields = ["id", "timestamp"]
    raw_id_fields = ["employee", "business"]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'business', 'employee')
        }),
        (_('Activity Details'), {
            'fields': ('model', 'action')
        }),
        (_('Timestamps'), {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )
    
    def action_display(self, obj):
        return obj.get_action_display()
    action_display.short_description = "Action"
    
    def model_display(self, obj):
        return obj.get_model_display()
    model_display.short_description = "Model"
    
    def employee_info(self, obj):
        if obj.employee and obj.employee.user:
            return obj.employee.user.email
        return "-"
    employee_info.short_description = "Employee"
    
    def business_name(self, obj):
        return obj.business.name if obj.business else "-"
    business_name.short_description = "Business"


@admin.register(BusinessImage)
class BusinessImageAdmin(admin.ModelAdmin):
    list_display = ["id", "business_name", "image_count", "created_at"]
    list_filter = ["business", "created_at"]
    search_fields = ["business__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["business"]
    filter_horizontal = ["image"]
    
    def business_name(self, obj):
        return obj.business.name if obj.business else "-"
    business_name.short_description = "Business"
    
    def image_count(self, obj):
        count = obj.image.count()
        return f"{count} images"
    image_count.short_description = "Images"

from django.contrib import admin
from .models import Plan, Download, Waitlist, FAQ, Contact


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'price', 'currency', 'billing_period')
	search_fields = ('name', 'price')
	ordering = ('name',)


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
	list_display = ('id', 'platform', 'download_link')
	search_fields = ('platform',)


@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
	list_display = ('id', 'email', 'created_at')
	search_fields = ('email',)
	readonly_fields = ('created_at',)
	ordering = ('-created_at',)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
	list_display = ('id', 'question')
	search_fields = ('question',)


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
	list_display = ('id', 'name', 'email', 'company', 'received_at')
	search_fields = ('name', 'email', 'company')
	readonly_fields = ('received_at',)
	ordering = ('-received_at',)

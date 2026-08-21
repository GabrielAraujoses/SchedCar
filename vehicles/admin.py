from django.contrib import admin

from .models import Brand, Vehicle


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
	list_display = ['name']
	search_fields = ['name']


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
	list_display = ['name', 'brand', 'license_plate', 'capacity', 'status', 'is_active']
	list_filter = ['status', 'is_active']
	search_fields = ['name', 'brand__name', 'license_plate']

from django.contrib import admin

from .models import ReferenceNumberCounter, Trip


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
	list_display = ['reference_number', 'employee', 'destination', 'date', 'vehicle', 'driver', 'status']
	list_filter = ['status', 'date']
	search_fields = ['reference_number', 'employee__employee_id', 'destination']
	readonly_fields = ['reference_number', 'requested_at', 'updated_at']


@admin.register(ReferenceNumberCounter)
class ReferenceNumberCounterAdmin(admin.ModelAdmin):
	list_display = ['year', 'last_number']

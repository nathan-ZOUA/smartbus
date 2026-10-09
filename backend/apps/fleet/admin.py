from django.contrib import admin

from .models import Bus, Driver


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ("registration", "make", "model", "status", "seats", "is_demo")
    list_filter = ("status", "is_demo", "make")
    search_fields = ("registration", "make", "model")


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("full_name", "license_number", "is_active", "is_demo")
    search_fields = ("full_name", "license_number", "phone")

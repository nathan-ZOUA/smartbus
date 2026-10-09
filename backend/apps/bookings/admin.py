from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("bus", "customer", "start_date", "end_date", "status", "total_price", "is_demo")
    list_filter = ("status", "is_demo")
    search_fields = ("bus__registration", "customer__username")

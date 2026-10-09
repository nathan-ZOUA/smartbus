from django.contrib import admin

from .models import GPSPosition


@admin.register(GPSPosition)
class GPSPositionAdmin(admin.ModelAdmin):
    list_display = ("bus", "latitude", "longitude", "speed_kph", "recorded_at", "is_demo")
    list_filter = ("is_demo",)
    date_hierarchy = "recorded_at"

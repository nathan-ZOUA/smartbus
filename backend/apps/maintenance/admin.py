from django.contrib import admin

from .models import MaintenanceOrder


@admin.register(MaintenanceOrder)
class MaintenanceOrderAdmin(admin.ModelAdmin):
    list_display = (
        "bus",
        "priority",
        "status",
        "estimated_cost",
        "actual_cost",
        "created_at",
    )
    list_filter = ("status", "priority")
    search_fields = ("bus__registration", "description")
    readonly_fields = (
        "created_by",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
    )

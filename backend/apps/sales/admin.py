from django.contrib import admin

from .models import SaleOrder


@admin.register(SaleOrder)
class SaleOrderAdmin(admin.ModelAdmin):
    list_display = (
        "bus",
        "customer",
        "amount",
        "currency",
        "status",
        "created_at",
    )
    list_filter = ("status", "currency")
    search_fields = ("bus__registration", "customer__username")
    readonly_fields = ("amount", "currency", "created_at", "updated_at")

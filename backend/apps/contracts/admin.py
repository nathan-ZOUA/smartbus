from django.contrib import admin

from .models import ContractDocument


@admin.register(ContractDocument)
class ContractDocumentAdmin(admin.ModelAdmin):
    list_display = ("reference", "kind", "customer", "status", "created_at")
    list_filter = ("kind", "status")
    search_fields = ("reference", "customer__username")
    readonly_fields = ("reference", "snapshot", "created_at")

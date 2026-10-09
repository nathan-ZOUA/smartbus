from django.contrib import admin

from .models import PaymentAttempt


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_reference",
        "customer",
        "amount",
        "currency",
        "status",
        "channel",
        "created_at",
    )
    list_filter = ("status", "channel", "currency")
    search_fields = (
        "transaction_reference",
        "customer__username",
        "booking__bus__registration",
        "sale_order__bus__registration",
    )
    readonly_fields = ("amount", "currency", "created_at", "reviewed_at")

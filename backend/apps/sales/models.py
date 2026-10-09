from django.conf import settings
from django.core.validators import MinValueValidator, StepValueValidator
from django.db import models
from django.db.models import Q

from apps.fleet.models import Bus


class SaleOrder(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Demande reçue"
        APPROVED = "APPROVED", "Vente approuvée"
        PAID = "PAID", "Payée"
        CANCELLED = "CANCELLED", "Annulée"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bus_sale_orders",
    )
    bus = models.ForeignKey(
        Bus,
        on_delete=models.PROTECT,
        related_name="sale_orders",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0), StepValueValidator(1)],
    )
    currency = models.CharField(max_length=3, default="XAF")
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"], name="sale_user_status_idx"),
            models.Index(fields=["bus", "status"], name="sale_bus_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name="sale_order_amount_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(currency="XAF"),
                name="sale_order_currency_xaf",
            ),
        ]

    def __str__(self):
        return f"{self.bus.registration} — {self.get_status_display()}"

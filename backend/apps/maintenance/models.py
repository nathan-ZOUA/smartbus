from django.conf import settings
from django.core.validators import MinValueValidator, StepValueValidator
from django.db import models

from apps.fleet.models import Bus


class MaintenanceOrder(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Demandée"
        APPROVED = "APPROVED", "Approuvée"
        IN_PROGRESS = "IN_PROGRESS", "En cours"
        COMPLETED = "COMPLETED", "Terminée"
        CANCELLED = "CANCELLED", "Annulée"

    class Priority(models.TextChoices):
        LOW = "LOW", "Faible"
        NORMAL = "NORMAL", "Normale"
        HIGH = "HIGH", "Haute"
        URGENT = "URGENT", "Urgente"

    bus = models.ForeignKey(
        Bus,
        on_delete=models.PROTECT,
        related_name="maintenance_orders",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_maintenance_orders",
    )
    description = models.TextField()
    priority = models.CharField(
        max_length=8,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )
    odometer_km = models.PositiveIntegerField(null=True, blank=True)
    estimated_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), StepValueValidator(1)],
    )
    actual_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), StepValueValidator(1)],
    )
    currency = models.CharField(max_length=3, default="XAF")
    previous_bus_status = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["bus", "status"], name="maint_bus_status_idx"),
        ]

    def __str__(self):
        return f"{self.bus.registration} — {self.get_status_display()}"

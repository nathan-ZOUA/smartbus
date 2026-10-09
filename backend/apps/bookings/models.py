from django.conf import settings
from django.core.validators import MinValueValidator, StepValueValidator
from django.db import models
from django.db.models import F, Q

from apps.fleet.models import Bus


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "En attente"
        CONFIRMED = "CONFIRMED", "Confirmée"
        PAID = "PAID", "Payée"
        CANCELLED = "CANCELLED", "Annulée"
        COMPLETED = "COMPLETED", "Terminée"

    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings")
    bus = models.ForeignKey(Bus, on_delete=models.PROTECT, related_name="bookings")
    start_date = models.DateField()
    end_date = models.DateField()
    destination = models.CharField(max_length=180)
    passengers = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0), StepValueValidator(1)],
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["bus", "start_date", "end_date"], name="booking_bus_dates_idx"),
            models.Index(fields=["customer", "status"], name="booking_user_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gt=F("start_date")), name="booking_end_after_start"),
            models.CheckConstraint(condition=Q(passengers__gte=1), name="booking_passengers_positive"),
        ]

    def __str__(self):
        return f"{self.bus.registration}: {self.start_date} – {self.end_date}"

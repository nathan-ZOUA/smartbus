from django.core.validators import MaxValueValidator, MinValueValidator, StepValueValidator
from django.db import models


class Driver(models.Model):
    full_name = models.CharField(max_length=160)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    license_number = models.CharField(max_length=80, unique=True)
    license_expires_at = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class Bus(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Disponible"
        IN_SERVICE = "IN_SERVICE", "En service"
        RENTED = "RENTED", "Loué"
        MAINTENANCE = "MAINTENANCE", "En maintenance"
        OFFLINE = "OFFLINE", "Hors ligne"
        FOR_SALE = "FOR_SALE", "À vendre"
        SOLD = "SOLD", "Vendu"

    registration = models.CharField(max_length=20, unique=True)
    make = models.CharField(max_length=80)
    model = models.CharField(max_length=80)
    year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1950), MaxValueValidator(2100)]
    )
    seats = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(200)])
    mileage_km = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    daily_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), StepValueValidator(1)],
    )
    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), StepValueValidator(1)],
    )
    driver = models.ForeignKey(Driver, null=True, blank=True, on_delete=models.SET_NULL, related_name="buses")
    description = models.TextField(blank=True)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["registration"]
        indexes = [
            models.Index(fields=["status", "seats"], name="bus_status_seats_idx"),
            models.Index(fields=["make", "model"], name="bus_make_model_idx"),
        ]

    def __str__(self):
        return f"{self.registration} — {self.make} {self.model}"

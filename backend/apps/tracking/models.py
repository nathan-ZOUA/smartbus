from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.fleet.models import Bus


class GPSPosition(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="positions")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.DecimalField(max_digits=9, decimal_places=6, validators=[MinValueValidator(-180), MaxValueValidator(180)])
    speed_kph = models.DecimalField(
        max_digits=6, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    heading = models.PositiveSmallIntegerField(default=0, validators=[MaxValueValidator(359)])
    recorded_at = models.DateTimeField(db_index=True)
    is_demo = models.BooleanField(default=False)

    class Meta:
        ordering = ["-recorded_at"]
        indexes = [models.Index(fields=["bus", "-recorded_at"], name="gps_bus_recorded_idx")]

    def __str__(self):
        return f"{self.bus.registration} @ {self.recorded_at}"

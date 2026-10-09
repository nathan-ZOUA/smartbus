from django.contrib.auth import get_user_model
from django.db import models

from apps.fleet.models import Driver


User = get_user_model()


class UserProfile(models.Model):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super administrateur"
        ADMIN = "ADMIN", "Administrateur"
        FLEET_MANAGER = "FLEET_MANAGER", "Gestionnaire de flotte"
        DRIVER = "DRIVER", "Conducteur"
        CLIENT = "CLIENT", "Client"
        SALES_AGENT = "SALES_AGENT", "Agent commercial"
        MAINTENANCE_MANAGER = "MAINTENANCE_MANAGER", "Responsable maintenance"

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    driver = models.ForeignKey(
        Driver,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="user_profiles",
    )
    phone = models.CharField(max_length=30, blank=True, default="")
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.CLIENT)
    is_demo = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

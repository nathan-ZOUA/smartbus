from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.fleet.models import Bus, Driver
from apps.tracking.models import GPSPosition


class Command(BaseCommand):
    help = "Crée ou met à jour des véhicules et positions clairement marqués Demo Data."

    def handle(self, *args, **options):
        driver, _ = Driver.objects.update_or_create(
            license_number="DEMO-LICENSE-001",
            defaults={
                "full_name": "Conducteur de démonstration",
                "phone": "",
                "email": "",
                "is_active": True,
                "is_demo": True,
            },
        )
        fixtures = [
            {
                "registration": "DEMO-SB-001",
                "make": "Demo Motors",
                "model": "City 40",
                "year": 2024,
                "seats": 40,
                "mileage_km": 18300,
                "status": Bus.Status.IN_SERVICE,
                "daily_rate": Decimal("320.00"),
                "driver": driver,
            },
            {
                "registration": "DEMO-SB-002",
                "make": "Demo Motors",
                "model": "Tour 52",
                "year": 2023,
                "seats": 52,
                "mileage_km": 26750,
                "status": Bus.Status.AVAILABLE,
                "daily_rate": Decimal("450.00"),
                "driver": None,
            },
        ]
        now = timezone.now()
        for index, fixture in enumerate(fixtures):
            bus, _ = Bus.objects.update_or_create(
                registration=fixture["registration"],
                defaults={**fixture, "is_demo": True},
            )
            if index == 0:
                position = GPSPosition.objects.filter(bus=bus, is_demo=True).first()
                values = {
                    "latitude": Decimal("48.856600"),
                    "longitude": Decimal("2.352200"),
                    "speed_kph": Decimal("32.50"),
                    "heading": 95,
                    "recorded_at": now - timedelta(seconds=25),
                    "is_demo": True,
                }
                if position:
                    for key, value in values.items():
                        setattr(position, key, value)
                    position.save(update_fields=list(values))
                else:
                    GPSPosition.objects.create(bus=bus, **values)
        self.stdout.write(self.style.SUCCESS("Données Demo Data créées/mises à jour."))

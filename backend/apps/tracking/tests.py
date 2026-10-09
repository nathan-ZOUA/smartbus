from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.fleet.models import Bus
from apps.users.models import UserProfile
from .models import GPSPosition


class TrackingApiTests(TestCase):
    def setUp(self):
        self.bus = Bus.objects.create(
            registration="SB-GPS-01",
            make="Demo",
            model="Coach",
            year=2024,
            seats=40,
            daily_rate="100.00",
        )

    def test_latest_returns_only_the_newest_position_per_bus(self):
        now = timezone.now()
        GPSPosition.objects.create(
            bus=self.bus,
            latitude=Decimal("48.000000"),
            longitude=Decimal("2.000000"),
            recorded_at=now - timedelta(minutes=5),
        )
        GPSPosition.objects.create(
            bus=self.bus,
            latitude=Decimal("48.500000"),
            longitude=Decimal("2.500000"),
            recorded_at=now,
        )

        user = get_user_model().objects.create_user(
            username="fleet-manager",
            password="a-very-strong-password",
        )
        UserProfile.objects.create(user=user, role=UserProfile.Role.FLEET_MANAGER)
        client = APIClient()
        client.force_authenticate(user)

        response = client.get(reverse("position-latest"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["latitude"], "48.500000")

    def test_gps_history_is_not_public(self):
        response = APIClient().get(reverse("position-latest"))

        self.assertEqual(response.status_code, 401)

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.fleet.models import Bus, Driver
from apps.tracking.models import GPSPosition
from apps.users.models import UserProfile


class DriverTrackingApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="phone-driver",
            password="a-very-strong-password",
        )
        self.driver = Driver.objects.create(
            full_name="Phone Driver",
            license_number="PHONE-DRIVER-001",
        )
        UserProfile.objects.create(
            user=self.user,
            role=UserProfile.Role.DRIVER,
            driver=self.driver,
        )
        self.bus = Bus.objects.create(
            registration="SB-PHONE-01",
            make="Demo",
            model="Coach",
            year=2024,
            seats=40,
            daily_rate="100.00",
            driver=self.driver,
        )
        self.other_driver = Driver.objects.create(
            full_name="Other Driver",
            license_number="PHONE-DRIVER-002",
        )
        self.other_bus = Bus.objects.create(
            registration="SB-PHONE-02",
            make="Demo",
            model="Coach",
            year=2024,
            seats=40,
            daily_rate="100.00",
            driver=self.other_driver,
        )
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.user).key}")

    def test_driver_can_list_only_assigned_buses(self):
        response = self.client.get(reverse("position-my-buses"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual([bus["id"] for bus in response.data], [self.bus.id])

    def test_driver_can_report_position_for_assigned_bus(self):
        response = self.client.post(
            reverse("position-report"),
            {
                "bus": self.bus.id,
                "latitude": "48.856600",
                "longitude": "2.352200",
                "speed_kph": "21.50",
                "heading": 90,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(GPSPosition.objects.filter(bus=self.bus).count(), 1)
        self.assertEqual(response.data["latitude"], "48.856600")

    def test_driver_cannot_report_position_for_another_bus(self):
        response = self.client.post(
            reverse("position-report"),
            {
                "bus": self.other_bus.id,
                "latitude": "48.856600",
                "longitude": "2.352200",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(GPSPosition.objects.exists())

    def test_driver_position_history_is_private_to_fleet_managers(self):
        response = self.client.get(reverse("position-latest"))

        self.assertEqual(response.status_code, 403)

    def test_ten_individual_drivers_can_report_their_own_bus_positions(self):
        User = get_user_model()
        for number in range(10):
            user = User.objects.create_user(
                username=f"pilot-driver-{number}",
                password="pilot-test-pass",
            )
            driver = Driver.objects.create(
                full_name=f"Pilot Driver {number}",
                license_number=f"PILOT-DRIVER-{number:03}",
            )
            UserProfile.objects.create(
                user=user,
                role=UserProfile.Role.DRIVER,
                driver=driver,
            )
            bus = Bus.objects.create(
                registration=f"SB-PILOT-{number:03}",
                make="Smart",
                model="Coach",
                year=2025,
                seats=40,
                daily_rate="100.00",
                driver=driver,
            )
            client = APIClient()
            client.force_authenticate(user)

            response = client.post(
                reverse("position-report"),
                {
                    "bus": bus.pk,
                    "latitude": "4.051100",
                    "longitude": "9.767900",
                    "speed_kph": "32.00",
                    "heading": number * 10,
                },
                format="json",
            )

            self.assertEqual(response.status_code, 201, response.data)

        self.assertEqual(GPSPosition.objects.count(), 10)

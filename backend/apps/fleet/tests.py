from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

from .models import Bus, Driver


class BusApiTests(TestCase):
    def setUp(self):
        self.bus = Bus.objects.create(
            registration="SB-TEST-01",
            make="Demo",
            model="Coach",
            year=2024,
            seats=40,
            daily_rate="350.00",
        )

    def test_bus_list_is_public_and_paginated(self):
        response = APIClient().get(reverse("bus-list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["registration"], "SB-TEST-01")

    def test_anonymous_cannot_create_bus(self):
        response = APIClient().post(
            reverse("bus-list"),
            {
                "registration": "SB-TEST-02",
                "make": "Demo",
                "model": "Coach",
                "year": 2024,
                "seats": 40,
                "daily_rate": "350.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_driver_records_are_not_public(self):
        response = APIClient().get(reverse("driver-list"))

        self.assertEqual(response.status_code, 401)

    def test_public_bus_list_does_not_expose_driver_identity(self):
        driver = Driver.objects.create(
            full_name="Private Driver",
            license_number="PRIVATE-DRIVER-01",
        )
        self.bus.driver = driver
        self.bus.save(update_fields=["driver"])

        response = APIClient().get(reverse("bus-list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("driver", response.data["results"][0])
        self.assertNotIn("driver_name", response.data["results"][0])

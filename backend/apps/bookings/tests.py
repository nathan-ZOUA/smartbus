from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from django.utils import timezone

from apps.fleet.models import Bus
from apps.users.models import UserProfile
from .models import Booking


class BookingApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="client",
            password="a-very-strong-password",
        )
        UserProfile.objects.create(user=self.user)
        self.bus = Bus.objects.create(
            registration="SB-BOOK-01",
            make="Demo",
            model="Coach",
            year=2024,
            seats=40,
            daily_rate="300.00",
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def payload(self, **overrides):
        data = {
            "bus": self.bus.pk,
            "start_date": "2027-02-01",
            "end_date": "2027-02-03",
            "destination": "Demo destination",
            "passengers": 20,
        }
        data.update(overrides)
        return data

    def test_booking_price_is_derived_and_user_is_scoped(self):
        response = self.client.post(reverse("booking-list"), self.payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(str(response.data["total_price"]), "600.00")
        self.assertEqual(response.data["customer"], self.user.pk)

    def test_overlapping_active_booking_is_rejected(self):
        Booking.objects.create(
            customer=self.user,
            bus=self.bus,
            start_date=date(2027, 2, 2),
            end_date=date(2027, 2, 4),
            destination="Existing trip",
            passengers=10,
            total_price="600.00",
        )

        response = self.client.post(reverse("booking-list"), self.payload(), format="json")

        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.data.get("id"))

    def test_booking_can_be_cancelled_once(self):
        response = self.client.post(reverse("booking-list"), self.payload(), format="json")
        cancel = self.client.post(
            reverse("booking-cancel", kwargs={"pk": response.data["id"]})
        )

        self.assertEqual(cancel.status_code, 200)
        self.assertEqual(cancel.data["status"], Booking.Status.CANCELLED)

    def test_booking_rejects_past_start_date(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        response = self.client.post(
            reverse("booking-list"),
            self.payload(start_date=yesterday.isoformat()),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("start_date", response.data)

    def test_bus_listed_for_sale_cannot_be_booked_for_rental(self):
        self.bus.status = Bus.Status.FOR_SALE
        self.bus.sale_price = "25000000.00"
        self.bus.save(update_fields=["status", "sale_price"])

        response = self.client.post(
            reverse("booking-list"),
            self.payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("bus", response.data)

    def test_xaf_daily_rate_must_be_an_integer(self):
        self.bus.daily_rate = "300.50"
        self.bus.save(update_fields=["daily_rate"])

        response = self.client.post(
            reverse("booking-list"),
            self.payload(),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("bus", response.data)

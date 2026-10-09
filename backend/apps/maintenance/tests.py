from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.fleet.models import Bus
from apps.maintenance.models import MaintenanceOrder
from apps.users.models import UserProfile
from apps.bookings.models import Booking


class MaintenanceOrderApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.manager = User.objects.create_user(
            username="maintenance-manager",
            password="example-not-used",
        )
        UserProfile.objects.create(
            user=self.manager,
            role=UserProfile.Role.MAINTENANCE_MANAGER,
        )
        self.customer = User.objects.create_user(
            username="maintenance-customer",
            password="example-not-used",
        )
        UserProfile.objects.create(user=self.customer)
        self.bus = Bus.objects.create(
            registration="SB-MAINT-01",
            make="Smart",
            model="Coach",
            year=2025,
            seats=40,
            mileage_km=50000,
        )
        self.manager_client = APIClient()
        self.manager_client.force_authenticate(self.manager)
        self.customer_client = APIClient()
        self.customer_client.force_authenticate(self.customer)

    def create_order(self):
        return MaintenanceOrder.objects.create(
            bus=self.bus,
            created_by=self.manager,
            description="Vidange et contrôle des freins",
            odometer_km=52000,
            estimated_cost="85000.00",
        )

    def test_manager_lifecycle_marks_bus_unavailable_and_restores_it(self):
        order = self.create_order()
        self.assertEqual(self.bus.status, Bus.Status.AVAILABLE)

        approved = self.manager_client.post(
            reverse("maintenance-order-approve", kwargs={"pk": order.pk})
        )
        self.assertEqual(approved.status_code, 200, approved.data)
        started = self.manager_client.post(
            reverse("maintenance-order-start", kwargs={"pk": order.pk})
        )
        self.assertEqual(started.status_code, 200, started.data)

        self.bus.refresh_from_db()
        self.assertEqual(self.bus.status, Bus.Status.MAINTENANCE)
        completed = self.manager_client.post(
            reverse("maintenance-order-complete", kwargs={"pk": order.pk}),
            {"actual_cost": "90000.00"},
            format="json",
        )
        self.assertEqual(completed.status_code, 200, completed.data)

        self.bus.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.bus.status, Bus.Status.AVAILABLE)
        self.assertEqual(self.bus.mileage_km, 52000)
        self.assertEqual(order.status, MaintenanceOrder.Status.COMPLETED)
        self.assertEqual(str(order.actual_cost), "90000.00")
        self.assertIsNotNone(order.completed_at)

    def test_only_authorized_staff_can_manage_maintenance(self):
        denied = self.customer_client.get(reverse("maintenance-order-list"))
        self.assertEqual(denied.status_code, 403)

        created = self.manager_client.post(
            reverse("maintenance-order-list"),
            {"bus": self.bus.pk, "description": "Contrôle périodique"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["currency"], "XAF")

    def test_cannot_complete_order_without_actual_cost(self):
        order = self.create_order()
        self.manager_client.post(
            reverse("maintenance-order-approve", kwargs={"pk": order.pk})
        )
        self.manager_client.post(
            reverse("maintenance-order-start", kwargs={"pk": order.pk})
        )

        response = self.manager_client.post(
            reverse("maintenance-order-complete", kwargs={"pk": order.pk}),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.bus.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.bus.status, Bus.Status.MAINTENANCE)
        self.assertEqual(order.status, MaintenanceOrder.Status.IN_PROGRESS)

    def test_maintenance_cannot_start_while_bus_has_an_active_booking(self):
        order = self.create_order()
        Booking.objects.create(
            customer=self.customer,
            bus=self.bus,
            start_date="2027-06-01",
            end_date="2027-06-02",
            destination="Douala",
            passengers=15,
            total_price="50000.00",
        )
        self.manager_client.post(
            reverse("maintenance-order-approve", kwargs={"pk": order.pk})
        )

        response = self.manager_client.post(
            reverse("maintenance-order-start", kwargs={"pk": order.pk})
        )

        self.assertEqual(response.status_code, 400)
        self.bus.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(self.bus.status, Bus.Status.AVAILABLE)
        self.assertEqual(order.status, MaintenanceOrder.Status.APPROVED)

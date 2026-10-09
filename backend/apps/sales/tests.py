from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.bookings.models import Booking
from apps.fleet.models import Bus
from apps.users.models import UserProfile

from .models import SaleOrder


class SaleOrderApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.customer = User.objects.create_user(
            username="sale-customer",
            password="example-not-used",
        )
        UserProfile.objects.create(user=self.customer)
        self.manager = User.objects.create_user(
            username="sales-manager",
            password="example-not-used",
        )
        UserProfile.objects.create(
            user=self.manager,
            role=UserProfile.Role.SALES_AGENT,
        )
        self.bus = Bus.objects.create(
            registration="SB-SALE-01",
            make="Smart",
            model="Coach",
            year=2025,
            seats=32,
            daily_rate="10000.00",
            sale_price="25000000.00",
            status=Bus.Status.FOR_SALE,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.customer)
        self.manager_client = APIClient()
        self.manager_client.force_authenticate(self.manager)

    def test_sale_price_is_server_controlled_and_requires_approval(self):
        response = self.client.post(
            reverse("sale-order-list"),
            {"bus": self.bus.pk, "amount": "1.00", "status": "PAID"},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["amount"], "25000000.00")
        self.assertEqual(response.data["currency"], "XAF")
        self.assertEqual(response.data["status"], SaleOrder.Status.REQUESTED)
        self.assertEqual(
            self.client.get(reverse("sale-order-list")).data["count"],
            1,
        )

        second_order = self.client.post(
            reverse("sale-order-list"),
            {"bus": self.bus.pk},
            format="json",
        )
        self.assertEqual(second_order.status_code, 400)

    def test_only_sales_manager_can_approve_and_customer_can_cancel(self):
        order = SaleOrder.objects.create(
            customer=self.customer,
            bus=self.bus,
            amount="25000000.00",
        )

        forbidden = self.client.post(
            reverse("sale-order-approve", kwargs={"pk": order.pk})
        )
        self.assertEqual(forbidden.status_code, 403)

        approved = self.manager_client.post(
            reverse("sale-order-approve", kwargs={"pk": order.pk})
        )
        self.assertEqual(approved.status_code, 200, approved.data)
        self.assertEqual(approved.data["status"], SaleOrder.Status.APPROVED)

        cancelled = self.client.post(
            reverse("sale-order-cancel", kwargs={"pk": order.pk})
        )
        self.assertEqual(cancelled.status_code, 200, cancelled.data)
        self.assertEqual(cancelled.data["status"], SaleOrder.Status.CANCELLED)

    def test_customer_cannot_view_another_customers_order(self):
        stranger = get_user_model().objects.create_user(
            username="other-sale-customer",
            password="example-not-used",
        )
        order = SaleOrder.objects.create(
            customer=stranger,
            bus=self.bus,
            amount="25000000.00",
        )

        response = self.client.get(
            reverse("sale-order-detail", kwargs={"pk": order.pk})
        )

        self.assertEqual(response.status_code, 404)

    def test_sale_cannot_be_approved_while_a_booking_is_active(self):
        order = SaleOrder.objects.create(
            customer=self.customer,
            bus=self.bus,
            amount="25000000.00",
        )
        Booking.objects.create(
            customer=self.customer,
            bus=self.bus,
            start_date="2027-05-01",
            end_date="2027-05-02",
            destination="Yaoundé",
            passengers=15,
            total_price="10000.00",
        )

        response = self.manager_client.post(
            reverse("sale-order-approve", kwargs={"pk": order.pk})
        )

        self.assertEqual(response.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, SaleOrder.Status.REQUESTED)

    def test_xaf_sale_price_must_be_an_integer(self):
        self.bus.sale_price = "25000000.50"
        self.bus.save(update_fields=["sale_price"])

        response = self.client.post(
            reverse("sale-order-list"),
            {"bus": self.bus.pk},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(SaleOrder.objects.exists())

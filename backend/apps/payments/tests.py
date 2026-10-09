from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from apps.bookings.models import Booking
from apps.fleet.models import Bus
from apps.payments.models import PaymentAttempt
from apps.sales.models import SaleOrder
from apps.users.models import UserProfile


@override_settings(
    ORANGE_MONEY_RECEIVER_NAME="SmartBus",
    ORANGE_MONEY_RECEIVER_NUMBER="690000000",
)
class PaymentAttemptApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.customer = User.objects.create_user(
            username="payment-customer",
            password="example-not-used",
        )
        UserProfile.objects.create(user=self.customer)
        self.other_customer = User.objects.create_user(
            username="other-payment-customer",
            password="example-not-used",
        )
        UserProfile.objects.create(user=self.other_customer)
        self.manager = User.objects.create_user(
            username="payment-manager",
            password="example-not-used",
        )
        UserProfile.objects.create(
            user=self.manager,
            role=UserProfile.Role.ADMIN,
        )
        self.rental_bus = Bus.objects.create(
            registration="SB-PAY-RENTAL",
            make="Smart",
            model="Coach",
            year=2025,
            seats=40,
            daily_rate="150000.00",
        )
        self.booking = Booking.objects.create(
            customer=self.customer,
            bus=self.rental_bus,
            start_date="2027-03-01",
            end_date="2027-03-03",
            destination="Douala",
            passengers=25,
            total_price="300000.00",
        )
        self.customer_client = APIClient()
        self.customer_client.force_authenticate(self.customer)
        self.other_customer_client = APIClient()
        self.other_customer_client.force_authenticate(self.other_customer)
        self.manager_client = APIClient()
        self.manager_client.force_authenticate(self.manager)

    def create_payment(self, **overrides):
        data = {
            "booking_id": self.booking.pk,
            "transaction_reference": "ORANGE-REF-1001",
            "sender_phone": "677000000",
        }
        data.update(overrides)
        return self.customer_client.post(
            reverse("payment-attempt-list"),
            data,
            format="json",
        )

    def test_instructions_expose_configured_orange_money_receiver(self):
        response = self.customer_client.get(reverse("payment-instructions"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["available"])
        self.assertEqual(response.data["channel"], "ORANGE_MONEY")
        self.assertEqual(response.data["currency"], "XAF")
        self.assertEqual(response.data["receiver_number"], "690000000")
        self.assertIn("manuelle", response.data["confirmation"])

    def test_payment_amount_is_server_controlled_and_manager_confirms_booking(self):
        response = self.create_payment(amount="1.00", status="VERIFIED")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["amount"], "300000.00")
        self.assertEqual(response.data["status"], PaymentAttempt.Status.PENDING)

        denied = self.customer_client.post(
            reverse("payment-attempt-verify", kwargs={"pk": response.data["id"]})
        )
        self.assertEqual(denied.status_code, 403)

        verified = self.manager_client.post(
            reverse("payment-attempt-verify", kwargs={"pk": response.data["id"]})
        )
        self.assertEqual(verified.status_code, 200, verified.data)
        self.assertEqual(verified.data["status"], PaymentAttempt.Status.VERIFIED)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PAID)

        duplicate = self.create_payment(transaction_reference="ORANGE-REF-1002")
        self.assertEqual(duplicate.status_code, 400)

    def test_customer_cannot_submit_payment_for_another_customers_booking(self):
        response = self.other_customer_client.post(
            reverse("payment-attempt-list"),
            {
                "booking_id": self.booking.pk,
                "transaction_reference": "ORANGE-REF-OTHER",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PaymentAttempt.objects.exists())

    def test_rejected_transaction_can_be_resubmitted_with_a_new_reference(self):
        response = self.create_payment()
        self.assertEqual(response.status_code, 201, response.data)

        rejected = self.manager_client.post(
            reverse("payment-attempt-reject", kwargs={"pk": response.data["id"]}),
            {"reason": "Référence introuvable dans Orange Money."},
            format="json",
        )
        self.assertEqual(rejected.status_code, 200, rejected.data)
        self.assertEqual(rejected.data["status"], PaymentAttempt.Status.REJECTED)

        retry = self.create_payment(transaction_reference="ORANGE-REF-1002")
        self.assertEqual(retry.status_code, 201, retry.data)

    def test_booking_cannot_be_cancelled_while_payment_needs_review(self):
        payment = self.create_payment()
        self.assertEqual(payment.status_code, 201, payment.data)

        response = self.customer_client.post(
            reverse("booking-cancel", kwargs={"pk": self.booking.pk})
        )

        self.assertEqual(response.status_code, 400)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, Booking.Status.PENDING)

    def test_verified_sale_payment_marks_the_vehicle_sold(self):
        bus = Bus.objects.create(
            registration="SB-PAY-SALE",
            make="Smart",
            model="Coach",
            year=2025,
            seats=32,
            daily_rate="150000.00",
            sale_price="20000000.00",
            status=Bus.Status.FOR_SALE,
        )
        sale = SaleOrder.objects.create(
            customer=self.customer,
            bus=bus,
            amount="20000000.00",
            status=SaleOrder.Status.APPROVED,
        )
        response = self.customer_client.post(
            reverse("payment-attempt-list"),
            {
                "sale_order_id": sale.pk,
                "transaction_reference": "ORANGE-REF-SALE",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)

        verified = self.manager_client.post(
            reverse("payment-attempt-verify", kwargs={"pk": response.data["id"]})
        )

        self.assertEqual(verified.status_code, 200, verified.data)
        sale.refresh_from_db()
        bus.refresh_from_db()
        self.assertEqual(sale.status, SaleOrder.Status.PAID)
        self.assertEqual(bus.status, Bus.Status.SOLD)

    @override_settings(ORANGE_MONEY_RECEIVER_NUMBER="")
    def test_payment_submission_requires_configured_receiver_number(self):
        response = self.create_payment()

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PaymentAttempt.objects.exists())

    def test_payment_rejects_fractional_xaf_amounts(self):
        self.booking.total_price = "300000.50"
        self.booking.save(update_fields=["total_price"])

        response = self.create_payment()

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PaymentAttempt.objects.exists())

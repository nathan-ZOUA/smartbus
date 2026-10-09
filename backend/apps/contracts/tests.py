from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.bookings.models import Booking
from apps.contracts.models import ContractDocument
from apps.fleet.models import Bus
from apps.sales.models import SaleOrder
from apps.users.models import UserProfile


class ContractDocumentApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.customer = user_model.objects.create_user(
            username="contract-customer",
            first_name="Nathan",
            last_name="Zoua",
            password="example-not-used",
        )
        UserProfile.objects.create(
            user=self.customer,
            phone="+237690000000",
        )
        self.other_customer = user_model.objects.create_user(
            username="other-contract-customer",
            password="example-not-used",
        )
        UserProfile.objects.create(user=self.other_customer)
        self.rental_bus = Bus.objects.create(
            registration="SB-CONTRACT-RENT",
            make="Smart",
            model="Coach",
            year=2025,
            seats=40,
            daily_rate="120000.00",
        )
        self.booking = Booking.objects.create(
            customer=self.customer,
            bus=self.rental_bus,
            start_date="2027-04-01",
            end_date="2027-04-04",
            destination="Yaoundé",
            passengers=25,
            total_price="360000.00",
            status=Booking.Status.PAID,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.customer)

    def test_paid_booking_generates_a_private_pdf_draft(self):
        response = self.client.get(
            reverse(
                "rental-contract-pdf",
                kwargs={"booking_id": self.booking.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))
        self.assertIn(b"attachment;", response["Content-Disposition"].encode())
        document = ContractDocument.objects.get(booking=self.booking)
        self.assertEqual(document.kind, ContractDocument.Kind.RENTAL)
        self.assertEqual(document.status, ContractDocument.Status.DRAFT)
        self.assertEqual(document.snapshot["customer_name"], "Nathan Zoua")
        self.assertEqual(document.snapshot["currency"], "XAF")
        self.assertEqual(
            document.snapshot["registration"],
            self.rental_bus.registration,
        )

        repeated = self.client.get(
            reverse(
                "rental-contract-pdf",
                kwargs={"booking_id": self.booking.pk},
            )
        )
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(ContractDocument.objects.filter(booking=self.booking).count(), 1)

    def test_contract_is_not_available_before_payment(self):
        self.booking.status = Booking.Status.PENDING
        self.booking.save(update_fields=["status"])

        response = self.client.get(
            reverse(
                "rental-contract-pdf",
                kwargs={"booking_id": self.booking.pk},
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(ContractDocument.objects.exists())

    def test_customer_cannot_download_another_customers_contract(self):
        self.booking.customer = self.other_customer
        self.booking.save(update_fields=["customer"])

        response = self.client.get(
            reverse(
                "rental-contract-pdf",
                kwargs={"booking_id": self.booking.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_paid_sale_generates_a_sale_contract_pdf(self):
        sale_bus = Bus.objects.create(
            registration="SB-CONTRACT-SALE",
            make="Smart",
            model="Coach",
            year=2025,
            seats=40,
            daily_rate="120000.00",
            sale_price="35000000.00",
            status=Bus.Status.SOLD,
        )
        sale_order = SaleOrder.objects.create(
            customer=self.customer,
            bus=sale_bus,
            amount="35000000.00",
            status=SaleOrder.Status.PAID,
        )

        response = self.client.get(
            reverse(
                "sale-contract-pdf",
                kwargs={"sale_order_id": sale_order.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))
        document = ContractDocument.objects.get(sale_order=sale_order)
        self.assertEqual(document.kind, ContractDocument.Kind.SALE)
        self.assertEqual(document.snapshot["amount"], "35000000.00")

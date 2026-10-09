from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions
from rest_framework.views import APIView

from apps.bookings.models import Booking
from apps.sales.models import SaleOrder

from .services import (
    can_access_contract,
    can_generate_rental_contract,
    can_generate_sale_contract,
    contract_pdf_response,
    create_rental_contract,
    create_sale_contract,
)


class RentalContractPdfView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def get(self, request, booking_id):
        booking = get_object_or_404(
            Booking.objects.select_related("customer", "bus"),
            pk=booking_id,
        )
        if not can_access_contract(request.user, booking.customer):
            raise Http404
        if not can_generate_rental_contract(booking):
            raise Http404("Le contrat est disponible après confirmation du paiement.")
        contract = create_rental_contract(booking)
        filename_date = timezone.localdate().strftime("%Y%m%d")
        response = contract_pdf_response(contract)
        response["X-Contract-Issued-Date"] = filename_date
        return response


class SaleContractPdfView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def get(self, request, sale_order_id):
        sale_order = get_object_or_404(
            SaleOrder.objects.select_related("customer", "bus"),
            pk=sale_order_id,
        )
        if not can_access_contract(request.user, sale_order.customer):
            raise Http404
        if not can_generate_sale_contract(sale_order):
            raise Http404("Le contrat est disponible après confirmation du paiement.")
        contract = create_sale_contract(sale_order)
        return contract_pdf_response(contract)

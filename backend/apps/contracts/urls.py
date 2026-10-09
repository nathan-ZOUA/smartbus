from django.urls import path

from .views import RentalContractPdfView, SaleContractPdfView


urlpatterns = [
    path(
        "bookings/<int:booking_id>/pdf/",
        RentalContractPdfView.as_view(),
        name="rental-contract-pdf",
    ),
    path(
        "sales/<int:sale_order_id>/pdf/",
        SaleContractPdfView.as_view(),
        name="sale-contract-pdf",
    ),
]

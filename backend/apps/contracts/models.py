import uuid

from django.conf import settings
from django.db import models

from apps.bookings.models import Booking
from apps.sales.models import SaleOrder


class ContractDocument(models.Model):
    class Kind(models.TextChoices):
        RENTAL = "RENTAL", "Location"
        SALE = "SALE", "Vente"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Brouillon à signer"

    reference = models.CharField(max_length=24, unique=True, editable=False)
    kind = models.CharField(max_length=8, choices=Kind.choices)
    booking = models.OneToOneField(
        Booking,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="contract_document",
    )
    sale_order = models.OneToOneField(
        SaleOrder,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="contract_document",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="contract_documents",
    )
    status = models.CharField(
        max_length=8,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(booking__isnull=False, sale_order__isnull=True)
                    | models.Q(booking__isnull=True, sale_order__isnull=False)
                ),
                name="contract_exactly_one_order",
            ),
        ]

    @staticmethod
    def make_reference(kind):
        prefix = "LOC" if kind == ContractDocument.Kind.RENTAL else "VEN"
        suffix = uuid.uuid4().hex[:12].upper()
        return f"SB-{prefix}-{suffix}"

    def __str__(self):
        return self.reference

from django.conf import settings
from django.core.validators import MinValueValidator, StepValueValidator
from django.db import models
from django.db.models import Q

from apps.bookings.models import Booking
from apps.sales.models import SaleOrder


class PaymentAttempt(models.Model):
    class Channel(models.TextChoices):
        ORANGE_MONEY = "ORANGE_MONEY", "Orange Money"

    class Status(models.TextChoices):
        PENDING = "PENDING", "À vérifier"
        VERIFIED = "VERIFIED", "Confirmé"
        REJECTED = "REJECTED", "Refusé"

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payment_attempts",
    )
    booking = models.ForeignKey(
        Booking,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_attempts",
    )
    sale_order = models.ForeignKey(
        SaleOrder,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="payment_attempts",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0), StepValueValidator(1)],
    )
    currency = models.CharField(max_length=3, default="XAF")
    channel = models.CharField(
        max_length=20,
        choices=Channel.choices,
        default=Channel.ORANGE_MONEY,
    )
    transaction_reference = models.CharField(max_length=100, unique=True)
    sender_phone = models.CharField(max_length=30, blank=True)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    review_note = models.CharField(max_length=250, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_payment_attempts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["customer", "status"], name="payment_user_status_idx"),
            models.Index(fields=["channel", "status"], name="payment_channel_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(booking__isnull=False, sale_order__isnull=True)
                    | Q(booking__isnull=True, sale_order__isnull=False)
                ),
                name="payment_exactly_one_order",
            ),
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="payment_amount_positive",
            ),
            models.CheckConstraint(
                condition=Q(currency="XAF"),
                name="payment_currency_xaf",
            ),
        ]

    def __str__(self):
        return f"{self.transaction_reference} — {self.get_status_display()}"

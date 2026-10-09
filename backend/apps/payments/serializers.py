from django.conf import settings
from django.db import transaction
from rest_framework import serializers

from apps.bookings.models import Booking
from apps.sales.models import SaleOrder

from .models import PaymentAttempt


class PaymentInstructionsSerializer(serializers.Serializer):
    available = serializers.SerializerMethodField()
    channel = serializers.CharField(default="ORANGE_MONEY")
    currency = serializers.CharField(default="XAF")
    receiver_name = serializers.SerializerMethodField()
    receiver_number = serializers.SerializerMethodField()
    confirmation = serializers.CharField(
        default="La confirmation est manuelle. SmartBus ne prélève pas automatiquement les fonds."
    )

    def get_available(self, obj):
        return bool(settings.ORANGE_MONEY_RECEIVER_NUMBER.strip())

    def get_receiver_name(self, obj):
        return settings.ORANGE_MONEY_RECEIVER_NAME.strip()

    def get_receiver_number(self, obj):
        return settings.ORANGE_MONEY_RECEIVER_NUMBER.strip()


class PaymentAttemptSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.username",
        read_only=True,
    )
    booking_id = serializers.IntegerField(
        required=False,
        write_only=True,
        allow_null=True,
    )
    sale_order_id = serializers.IntegerField(
        required=False,
        write_only=True,
        allow_null=True,
    )
    bus_registration = serializers.SerializerMethodField()
    order_reference = serializers.SerializerMethodField()
    reviewed_by_name = serializers.CharField(
        source="reviewed_by.username",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = PaymentAttempt
        fields = [
            "id",
            "booking",
            "booking_id",
            "sale_order",
            "sale_order_id",
            "order_reference",
            "bus_registration",
            "amount",
            "currency",
            "channel",
            "transaction_reference",
            "sender_phone",
            "status",
            "review_note",
            "reviewed_by",
            "reviewed_by_name",
            "customer_name",
            "created_at",
            "reviewed_at",
        ]
        read_only_fields = [
            "id",
            "booking",
            "sale_order",
            "amount",
            "currency",
            "channel",
            "status",
            "review_note",
            "reviewed_by",
            "reviewed_by_name",
            "customer_name",
            "created_at",
            "reviewed_at",
        ]
        extra_kwargs = {
            "transaction_reference": {"required": True, "max_length": 100},
            "sender_phone": {
                "required": False,
                "allow_blank": True,
                "max_length": 30,
            },
        }

    def get_bus_registration(self, payment):
        if payment.booking_id:
            return payment.booking.bus.registration
        return payment.sale_order.bus.registration

    def get_order_reference(self, payment):
        if payment.booking_id:
            return f"RES-{payment.booking_id}"
        return f"VTE-{payment.sale_order_id}"

    def validate(self, attrs):
        booking_id = attrs.get("booking_id")
        sale_order_id = attrs.get("sale_order_id")
        if bool(booking_id) == bool(sale_order_id):
            raise serializers.ValidationError(
                "Indique soit booking_id, soit sale_order_id, mais pas les deux."
            )
        if not settings.ORANGE_MONEY_RECEIVER_NUMBER.strip():
            raise serializers.ValidationError(
                "Le numéro destinataire Orange Money doit être configuré avant d'activer les paiements."
            )

        user = self.context["request"].user
        if booking_id:
            booking = Booking.objects.filter(pk=booking_id).first()
            if booking is None or booking.customer_id != user.pk:
                raise serializers.ValidationError(
                    {"booking_id": "Réservation introuvable pour ce compte."}
                )
            if booking.status not in {
                Booking.Status.PENDING,
                Booking.Status.CONFIRMED,
            }:
                raise serializers.ValidationError(
                    {"booking_id": "Cette réservation ne peut plus être payée."}
                )
            if booking.total_price <= 0:
                raise serializers.ValidationError(
                    {"booking_id": "Le montant de la réservation doit être supérieur à zéro."}
                )
            attrs["booking"] = booking
            attrs["amount"] = booking.total_price
        else:
            sale_order = SaleOrder.objects.select_related("bus").filter(
                pk=sale_order_id
            ).first()
            if sale_order is None or sale_order.customer_id != user.pk:
                raise serializers.ValidationError(
                    {"sale_order_id": "Demande de vente introuvable pour ce compte."}
                )
            if sale_order.status != SaleOrder.Status.APPROVED:
                raise serializers.ValidationError(
                    {"sale_order_id": "La vente doit être approuvée avant son paiement."}
                )
            if sale_order.bus.sale_price != sale_order.amount:
                raise serializers.ValidationError(
                    {"sale_order_id": "Le prix du véhicule a changé; fais vérifier la vente par l'agence."}
                )
            attrs["sale_order"] = sale_order
            attrs["amount"] = sale_order.amount
        if attrs["amount"] != attrs["amount"].to_integral_value():
            raise serializers.ValidationError(
                "Les montants en XAF doivent être des nombres entiers."
            )
        attrs.pop("booking_id", None)
        attrs.pop("sale_order_id", None)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        booking = validated_data.get("booking")
        sale_order = validated_data.get("sale_order")
        if booking:
            booking = Booking.objects.select_for_update().get(pk=booking.pk)
            if booking.status not in {
                Booking.Status.PENDING,
                Booking.Status.CONFIRMED,
            }:
                raise serializers.ValidationError(
                    {"booking_id": "Cette réservation ne peut plus être payée."}
                )
            pending_payment = PaymentAttempt.objects.filter(
                booking=booking,
                status__in=[
                    PaymentAttempt.Status.PENDING,
                    PaymentAttempt.Status.VERIFIED,
                ],
            ).exists()
            if pending_payment:
                raise serializers.ValidationError(
                    {"booking_id": "Un paiement est déjà en cours ou confirmé."}
                )
            validated_data["booking"] = booking
        else:
            sale_order = SaleOrder.objects.select_for_update().get(
                pk=sale_order.pk
            )
            if sale_order.status != SaleOrder.Status.APPROVED:
                raise serializers.ValidationError(
                    {"sale_order_id": "La vente doit être approuvée avant son paiement."}
                )
            if sale_order.bus.sale_price != sale_order.amount:
                raise serializers.ValidationError(
                    {"sale_order_id": "Le prix du véhicule a changé; fais vérifier la vente par l'agence."}
                )
            pending_payment = PaymentAttempt.objects.filter(
                sale_order=sale_order,
                status__in=[
                    PaymentAttempt.Status.PENDING,
                    PaymentAttempt.Status.VERIFIED,
                ],
            ).exists()
            if pending_payment:
                raise serializers.ValidationError(
                    {"sale_order_id": "Un paiement est déjà en cours ou confirmé."}
                )
            validated_data["sale_order"] = sale_order

        validated_data["customer"] = self.context["request"].user
        validated_data["currency"] = "XAF"
        validated_data["channel"] = PaymentAttempt.Channel.ORANGE_MONEY
        return super().create(validated_data)

from django.utils import timezone
from rest_framework import serializers

from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source="customer.username", read_only=True)
    bus_registration = serializers.CharField(source="bus.registration", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "customer", "customer_name", "bus", "bus_registration", "start_date",
            "end_date", "destination", "passengers", "total_price", "status",
            "is_demo", "created_at",
        ]
        read_only_fields = ["id", "customer", "total_price", "status", "is_demo", "created_at"]

    def validate(self, attrs):
        if attrs["end_date"] <= attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "La date de retour doit être après le départ."})
        if attrs["start_date"] < timezone.localdate():
            raise serializers.ValidationError({"start_date": "La date de départ ne peut pas être dans le passé."})
        if attrs["passengers"] > attrs["bus"].seats:
            raise serializers.ValidationError({"passengers": "Le nombre de passagers dépasse la capacité du bus."})
        if attrs["bus"].status in {
            "MAINTENANCE", "OFFLINE", "RENTED", "SOLD", "FOR_SALE"
        }:
            raise serializers.ValidationError({"bus": "Ce bus n'est pas disponible à la réservation."})
        if attrs["bus"].daily_rate != attrs["bus"].daily_rate.to_integral_value():
            raise serializers.ValidationError(
                {"bus": "Le tarif de location en XAF doit être un nombre entier."}
            )
        return attrs

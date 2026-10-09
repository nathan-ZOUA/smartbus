from rest_framework import serializers

from apps.fleet.models import Bus

from .models import MaintenanceOrder


class MaintenanceOrderSerializer(serializers.ModelSerializer):
    bus_registration = serializers.CharField(
        source="bus.registration",
        read_only=True,
    )
    currency = serializers.CharField(read_only=True)

    class Meta:
        model = MaintenanceOrder
        fields = [
            "id",
            "bus",
            "bus_registration",
            "description",
            "priority",
            "status",
            "odometer_km",
            "estimated_cost",
            "actual_cost",
            "currency",
            "created_by",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "actual_cost",
            "currency",
            "created_by",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
        ]

    def validate_bus(self, bus):
        if bus.status in {
            Bus.Status.RENTED,
            Bus.Status.SOLD,
            Bus.Status.MAINTENANCE,
        }:
            raise serializers.ValidationError(
                "Ce bus n'est pas disponible pour un nouvel ordre de maintenance."
            )
        return bus

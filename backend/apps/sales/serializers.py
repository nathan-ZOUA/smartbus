from rest_framework import serializers

from .models import SaleOrder


class SaleOrderSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(
        source="customer.username",
        read_only=True,
    )
    bus_registration = serializers.CharField(
        source="bus.registration",
        read_only=True,
    )
    bus_make = serializers.CharField(source="bus.make", read_only=True)
    bus_model = serializers.CharField(source="bus.model", read_only=True)

    class Meta:
        model = SaleOrder
        fields = [
            "id",
            "customer",
            "customer_name",
            "bus",
            "bus_registration",
            "bus_make",
            "bus_model",
            "amount",
            "currency",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "customer",
            "amount",
            "currency",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate_bus(self, bus):
        from apps.fleet.models import Bus

        if bus.status != Bus.Status.FOR_SALE or bus.sale_price is None or bus.sale_price <= 0:
            raise serializers.ValidationError(
                "Ce véhicule n'est pas actuellement en vente."
            )
        if bus.sale_price != bus.sale_price.to_integral_value():
            raise serializers.ValidationError(
                "Le prix de vente en XAF doit être un nombre entier."
            )
        return bus

from rest_framework import serializers

from .models import Bus, Driver


class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = ["id", "full_name", "phone", "email", "license_number", "license_expires_at", "is_active", "is_demo"]


class BusSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source="driver.full_name", read_only=True, default=None)

    class Meta:
        model = Bus
        fields = [
            "id", "registration", "make", "model", "year", "seats", "mileage_km",
            "status", "daily_rate", "sale_price", "driver", "driver_name",
            "description", "is_demo", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "is_demo"]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request")
        user = getattr(request, "user", None)
        profile = getattr(user, "profile", None) if user and user.is_authenticated else None
        can_view_driver = bool(
            user
            and user.is_authenticated
            and (
                user.is_staff
                or (profile and profile.role in {"SUPER_ADMIN", "ADMIN", "FLEET_MANAGER"})
            )
        )
        if not can_view_driver:
            data.pop("driver", None)
            data.pop("driver_name", None)
        return data

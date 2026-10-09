from rest_framework import serializers

from .models import GPSPosition


class GPSPositionSerializer(serializers.ModelSerializer):
    registration = serializers.CharField(source="bus.registration", read_only=True)

    class Meta:
        model = GPSPosition
        fields = ["id", "bus", "registration", "latitude", "longitude", "speed_kph", "heading", "recorded_at", "is_demo"]
        read_only_fields = ["id", "recorded_at", "is_demo"]

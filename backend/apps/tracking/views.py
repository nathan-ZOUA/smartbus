from django.db.models import OuterRef, Subquery
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from apps.fleet.models import Bus
from apps.users.models import UserProfile
from .models import GPSPosition
from .serializers import GPSPositionSerializer


class TrackingAccessPermission(BasePermission):
    allowed_roles = {"SUPER_ADMIN", "ADMIN", "FLEET_MANAGER"}

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff or request.user.is_superuser:
            return True
        profile = getattr(request.user, "profile", None)
        return bool(profile and profile.role in self.allowed_roles)


class DriverTrackingPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        profile = getattr(request.user, "profile", None)
        return bool(
            profile
            and profile.role == UserProfile.Role.DRIVER
            and profile.driver_id
            and profile.driver.is_active
        )


class GPSReportThrottle(UserRateThrottle):
    scope = "gps_report"


class GPSPositionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GPSPosition.objects.select_related("bus").all()
    serializer_class = GPSPositionSerializer
    permission_classes = [TrackingAccessPermission]
    filterset_fields = ["bus"]

    @action(detail=False, methods=["get"], url_path="latest")
    def latest(self, request):
        newest_position = GPSPosition.objects.filter(bus_id=OuterRef("pk")).order_by(
            "-recorded_at", "-id"
        )
        rows = GPSPosition.objects.filter(
            pk__in=Bus.objects.filter(positions__isnull=False)
            .annotate(newest_id=Subquery(newest_position.values("id")[:1]))
            .values("newest_id")
        ).select_related("bus").order_by("bus__registration")
        return Response(self.get_serializer(rows, many=True).data)

    @action(
        detail=False,
        methods=["post"],
        permission_classes=[permissions.IsAuthenticated],
        throttle_classes=[GPSReportThrottle],
    )
    def report(self, request):
        profile = getattr(request.user, "profile", None)
        is_manager = bool(
            request.user.is_staff
            or (profile and profile.role in {"SUPER_ADMIN", "ADMIN", "FLEET_MANAGER"})
        )
        is_assigned_driver = bool(
            profile
            and profile.role == UserProfile.Role.DRIVER
            and profile.driver_id
            and profile.driver.is_active
        )
        if not (is_manager or is_assigned_driver):
            return Response({"detail": "Permission refusée."}, status=403)
        serializer = GPSPositionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bus = serializer.validated_data["bus"]
        if is_assigned_driver and not is_manager:
            if not Bus.objects.filter(pk=bus.pk, driver_id=profile.driver_id).exists():
                return Response(
                    {"detail": "Ce bus n'est pas affecté à votre compte conducteur."},
                    status=403,
                )
        position = GPSPosition.objects.create(**serializer.validated_data, recorded_at=timezone.now())
        if bus.status in {Bus.Status.OFFLINE, Bus.Status.AVAILABLE}:
            bus.status = Bus.Status.IN_SERVICE
            bus.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(position).data, status=201)

    @action(
        detail=False,
        methods=["get"],
        url_path="my-buses",
        permission_classes=[DriverTrackingPermission],
    )
    def my_buses(self, request):
        profile = request.user.profile
        buses = Bus.objects.filter(driver_id=profile.driver_id).order_by("registration")
        return Response(
            [
                {"id": bus.id, "registration": bus.registration, "status": bus.status}
                for bus in buses
            ]
        )

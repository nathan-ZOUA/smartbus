from django.utils import timezone

from apps.bookings.models import Booking


def bus_has_active_bookings(bus):
    return Booking.objects.filter(
        bus=bus,
        end_date__gte=timezone.localdate(),
    ).exclude(
        status__in=[Booking.Status.CANCELLED, Booking.Status.COMPLETED]
    ).exists()

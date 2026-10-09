from rest_framework.permissions import BasePermission, SAFE_METHODS


class FleetWritePermission(BasePermission):
    write_roles = {"SUPER_ADMIN", "ADMIN", "FLEET_MANAGER"}

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff or request.user.is_superuser:
            return True
        profile = getattr(request.user, "profile", None)
        return bool(profile and profile.role in self.write_roles)


class DriverManagementPermission(BasePermission):
    allowed_roles = FleetWritePermission.write_roles

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_staff or request.user.is_superuser:
            return True
        profile = getattr(request.user, "profile", None)
        return bool(profile and profile.role in self.allowed_roles)

from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.users.models import UserProfile
from .serializers import LoginSerializer, RegistrationSerializer


class AuthenticationRateThrottle(AnonRateThrottle):
    scope = "auth"


def effective_role(user, profile):
    if user.is_superuser:
        return "SUPER_ADMIN"
    if user.is_staff:
        return "ADMIN"
    return profile.role


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([AuthenticationRateThrottle])
def register(request):
    serializer = RegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(
        {
            "token": user.auth_token.key,
            "user": {
                "id": user.pk,
                "username": user.username,
                "email": user.email,
                "role": effective_role(user, user.profile),
            },
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([AuthenticationRateThrottle])
def login(request):
    serializer = LoginSerializer(data=request.data, context={"request": request})
    serializer.is_valid(raise_exception=True)
    token, _ = Token.objects.get_or_create(user=serializer.validated_data["user"])
    user = serializer.validated_data["user"]
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return Response(
        {
            "token": token.key,
            "user": {
                "id": user.pk,
                "username": user.username,
                "email": user.email,
                "role": effective_role(user, profile),
            },
        }
    )


@api_view(["POST"])
def logout(request):
    request.auth.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
def me(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return Response(
        {
            "id": request.user.pk,
            "username": request.user.username,
            "email": request.user.email,
            "role": effective_role(request.user, profile),
        }
    )

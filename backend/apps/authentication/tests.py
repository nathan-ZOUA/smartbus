from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APITestCase
from django.urls import reverse

from rest_framework.authtoken.models import Token
from django.utils import timezone


class AuthenticationApiTests(APITestCase):
    def test_registration_creates_client_and_returns_token(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-client",
                "email": "client@example.test",
                "password": "a-very-strong-password",
                "password_confirm": "a-very-strong-password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["token"])
        user = get_user_model().objects.get(username="new-client")
        self.assertEqual(user.profile.role, "CLIENT")

    def test_registration_rejects_mismatched_passwords(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-client",
                "email": "client@example.test",
                "password": "a-very-strong-password",
                "password_confirm": "different-strong-password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_login_and_logout_revoke_token(self):
        user = get_user_model().objects.create_user(
            username="client",
            password="a-very-strong-password",
            email="client@example.test",
        )

        login = self.client.post(
            reverse("login"),
            {"username": "client", "password": "a-very-strong-password"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {login.data['token']}")
        self.assertEqual(self.client.get(reverse("me")).status_code, 200)

        logout = self.client.post(reverse("logout"))
        self.assertEqual(logout.status_code, 204)
        self.assertFalse(Token.objects.filter(user=user).exists())

    @override_settings(SMARTBUS_TOKEN_TTL_HOURS=12)
    def test_expired_token_is_rejected_and_revoked(self):
        user = get_user_model().objects.create_user(
            username="expired-client",
            password="a-very-strong-password",
        )
        token = Token.objects.create(user=user)
        token.created = timezone.now() - timedelta(hours=13)
        token.save(update_fields=["created"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

        response = self.client.get(reverse("me"))

        self.assertEqual(response.status_code, 401)
        self.assertFalse(Token.objects.filter(pk=token.pk).exists())

    def test_superuser_receives_super_admin_role(self):
        get_user_model().objects.create_superuser(
            username="root-admin",
            email="root@example.test",
            password="a-very-strong-password",
        )

        response = self.client.post(
            reverse("login"),
            {"username": "root-admin", "password": "a-very-strong-password"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], "SUPER_ADMIN")

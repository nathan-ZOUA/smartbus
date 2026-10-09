from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import UserProfile


class UserProfileTests(TestCase):
    def test_role_defaults_to_client_and_is_not_demo(self):
        user = get_user_model().objects.create_user(
            username="customer",
            password="a-strong-test-password",
        )

        profile = UserProfile.objects.create(user=user)

        self.assertEqual(profile.role, UserProfile.Role.CLIENT)
        self.assertFalse(profile.is_demo)

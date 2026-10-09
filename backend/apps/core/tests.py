from django.test import SimpleTestCase
from django.urls import reverse


class ApiRootTests(SimpleTestCase):
    def test_api_root_returns_project_status(self):
        response = self.client.get(reverse("smartbus-api-root"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "SmartBus API")
        self.assertEqual(response.json()["status"], "ready")

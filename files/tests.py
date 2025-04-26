from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

User = get_user_model()


class SignUrlViewsetTest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            first_name="testuser", email="test@example.com", password="testpass123"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("signed-url-list")

    def test_successful_signed_url_request(self):
        payload = {"hash": "examplehash", "size": 500, "ext": "jpg"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertIn("signed_url", response.data)

    def test_invalid_extension_request(self):
        payload = {"hash": "examplehash", "size": 500, "ext": "exe"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("ext", response.data)

    def test_missing_fields_request(self):
        payload = {
            "hash": "examplehash",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("size", response.data)
        self.assertIn("ext", response.data)

    def test_unauthenticated_request(self):
        self.client.logout()
        payload = {"hash": "examplehash", "size": 500, "ext": "jpg"}
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import FAQ, Contact, Download, Plan, Waitlist


class AdministrationEndpointsTest(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_list_plans_and_faqs(self):
        Plan.objects.create(
            name="Basic",
            price="10.00",
            currency="USD",
            billing_period="monthly",
            features=["a", "b"],
        )
        FAQ.objects.create(question="Q1?", answer="A1")

        plans_resp = self.client.get("/administration/plans/")
        self.assertEqual(plans_resp.status_code, status.HTTP_200_OK)
        plans_data = (
            plans_resp.data.get("results")
            if isinstance(plans_resp.data, dict)
            else plans_resp.data
        )
        self.assertIsInstance(plans_data, list)
        self.assertGreaterEqual(len(plans_data), 1)

        faqs_resp = self.client.get("/administration/faqs/")
        self.assertEqual(faqs_resp.status_code, status.HTTP_200_OK)
        faqs_data = (
            faqs_resp.data.get("results")
            if isinstance(faqs_resp.data, dict)
            else faqs_resp.data
        )
        self.assertIsInstance(faqs_data, list)
        self.assertGreaterEqual(len(faqs_data), 1)

    def test_waitlist_create_and_duplicate(self):
        url = "/administration/waitlist/"
        payload = {"email": "user@example.com"}

        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", resp.data)
        self.assertEqual(resp.data.get("email"), payload["email"])

        resp2 = self.client.post(url, payload, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", resp2.data)

    def test_contact_create_and_validation(self):
        url = "/administration/contacts/"
        good_payload = {
            "name": "John Doe",
            "email": "john@example.com",
            "message": "This is a valid message.",
        }

        resp = self.client.post(url, good_payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", resp.data)
        self.assertIn("received_at", resp.data)

        bad_payload = {
            "name": "John Doe",
            "email": "john2@example.com",
            "message": "short",
        }
        resp2 = self.client.post(url, bad_payload, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("message", resp2.data)

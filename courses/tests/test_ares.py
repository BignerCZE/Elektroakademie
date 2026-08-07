from unittest.mock import Mock, patch

import requests
from django.test import TestCase
from django.urls import reverse


class AresCompanyDetailTests(TestCase):
    def get_url(self, ico="12345678"):
        return reverse(
            "ares_company_detail",
            kwargs={"ico": ico},
        )

    @patch("courses.views.requests.get")
    def test_invalid_ico_returns_400_without_ares_request(
        self,
        mock_get,
    ):
        response = self.client.get(
            self.get_url("12345")
        )

        self.assertEqual(
            response.status_code,
            400,
        )

        payload = response.json()

        self.assertFalse(
            payload["success"]
        )

        self.assertEqual(
            payload["message"],
            "IČO musí obsahovat přesně 8 číslic.",
        )

        mock_get.assert_not_called()

    @patch("courses.views.requests.get")
    def test_ico_is_normalized_before_ares_request(
        self,
        mock_get,
    ):
        ares_response = Mock()
        ares_response.status_code = 200
        ares_response.ok = True
        ares_response.json.return_value = {
            "ico": "12345678",
            "obchodniJmeno": "Test s.r.o.",
            "sidlo": {},
        }

        mock_get.return_value = ares_response

        response = self.client.get(
            self.get_url("123-456-78")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        mock_get.assert_called_once_with(
            (
                "https://ares.gov.cz/"
                "ekonomicke-subjekty-v-be/rest/"
                "ekonomicke-subjekty/12345678"
            ),
            timeout=8,
            headers={
                "Accept": "application/json",
                "User-Agent": "Elektroakademie/1.0",
            },
        )

    @patch("courses.views.requests.get")
    def test_valid_ares_response_is_mapped_correctly(
        self,
        mock_get,
    ):
        ares_response = Mock()
        ares_response.status_code = 200
        ares_response.ok = True
        ares_response.json.return_value = {
            "ico": "12345678",
            "dic": "CZ12345678",
            "obchodniJmeno": "Testovací firma s.r.o.",
            "sidlo": {
                "nazevUlice": "Dlouhá",
                "cisloDomovni": 123,
                "cisloOrientacni": 45,
                "nazevObce": "Praha",
                "psc": 11000,
                "nazevStatu": "Česká republika",
            },
        }

        mock_get.return_value = ares_response

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        payload = response.json()

        self.assertTrue(
            payload["success"]
        )

        self.assertEqual(
            payload["company"],
            {
                "ico": "12345678",
                "dic": "CZ12345678",
                "name": "Testovací firma s.r.o.",
                "street": "Dlouhá 123/45",
                "city": "Praha",
                "postal_code": "11000",
                "country": "Česká republika",
            },
        )

    @patch("courses.views.requests.get")
    def test_address_uses_part_of_city_when_street_is_missing(
        self,
        mock_get,
    ):
        ares_response = Mock()
        ares_response.status_code = 200
        ares_response.ok = True
        ares_response.json.return_value = {
            "ico": "12345678",
            "obchodniJmeno": "Testovací firma",
            "sidlo": {
                "nazevCastiObce": "Horní Lhota",
                "cisloDomovni": 25,
                "nazevObce": "Lhota",
                "psc": 12345,
            },
        }

        mock_get.return_value = ares_response

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        company = response.json()["company"]

        self.assertEqual(
            company["street"],
            "Horní Lhota 25",
        )

        self.assertEqual(
            company["country"],
            "Česká republika",
        )

    @patch("courses.views.requests.get")
    def test_missing_company_returns_404(
        self,
        mock_get,
    ):
        ares_response = Mock()
        ares_response.status_code = 404
        ares_response.ok = False

        mock_get.return_value = ares_response

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        payload = response.json()

        self.assertFalse(
            payload["success"]
        )

        self.assertEqual(
            payload["message"],
            "Subjekt s tímto IČO nebyl nalezen.",
        )

    @patch("courses.views.requests.get")
    def test_ares_server_error_returns_502(
        self,
        mock_get,
    ):
        ares_response = Mock()
        ares_response.status_code = 500
        ares_response.ok = False

        mock_get.return_value = ares_response

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            502,
        )

        payload = response.json()

        self.assertFalse(
            payload["success"]
        )

        self.assertEqual(
            payload["message"],
            "Nepodařilo se načíst údaje z ARES.",
        )

    @patch("courses.views.requests.get")
    def test_ares_connection_error_returns_503(
        self,
        mock_get,
    ):
        mock_get.side_effect = (
            requests.RequestException(
                "ARES connection failed"
            )
        )

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            503,
        )

        payload = response.json()

        self.assertFalse(
            payload["success"]
        )

        self.assertEqual(
            payload["message"],
            "ARES je momentálně nedostupný.",
        )

    @patch("courses.views.requests.get")
    def test_invalid_ares_json_returns_502(
        self,
        mock_get,
    ):
        ares_response = Mock()
        ares_response.status_code = 200
        ares_response.ok = True
        ares_response.json.side_effect = ValueError(
            "Invalid JSON"
        )

        mock_get.return_value = ares_response

        response = self.client.get(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            502,
        )

        payload = response.json()

        self.assertFalse(
            payload["success"]
        )

        self.assertEqual(
            payload["message"],
            "Nepodařilo se načíst údaje z ARES.",
        )

    def test_ares_endpoint_requires_get(self):
        response = self.client.post(
            self.get_url()
        )

        self.assertEqual(
            response.status_code,
            405,
        )
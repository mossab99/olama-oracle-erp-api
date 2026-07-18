import unittest
from unittest.mock import patch

from app import create_app
from config import Config


class TransportMasterRouteTests(unittest.TestCase):
    def setUp(self):
        app = create_app()
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.headers = {"X-API-Key": Config.API_SECRET_KEY}

    def test_master_endpoints_require_api_key(self):
        self.assertEqual(
            self.client.get("/api/transportation/buses").status_code, 401
        )
        self.assertEqual(
            self.client.get("/api/transportation/regions").status_code, 401
        )

    @patch("routes.transportation.get_transportation_buses")
    def test_buses_contract(self, get_buses):
        get_buses.return_value = [{
            "oracle_bus_id": 1,
            "bus_number": 3,
            "registered_capacity": 23,
        }]
        response = self.client.get(
            "/api/transportation/buses", headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["buses"][0]["oracle_bus_id"], 1)

    @patch("routes.transportation.get_transportation_regions")
    def test_regions_contract(self, get_regions):
        get_regions.return_value = [{
            "oracle_region_id": 89,
            "family_count": 12,
            "student_count": 18,
        }]
        response = self.client.get(
            "/api/transportation/regions?study_year=2026%2F2027",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        get_regions.assert_called_once_with("2026/2027")


if __name__ == "__main__":
    unittest.main()

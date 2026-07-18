import unittest
from unittest.mock import patch

from app import create_app
from config import Config
from repositories.transportation_repo import (
    get_transportation_buses,
    get_transportation_regions,
)


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


class TransportMasterRepositoryTests(unittest.TestCase):
    @patch("repositories.transportation_repo.query_all")
    def test_bus_identity_uses_assignment_number_and_confirmed_fields(self, query_all):
        query_all.side_effect = [
            [
                {"column_name": "BUS_SCHOOL_ID"},
                {"column_name": "BUS_SCHOOL_NUMBER"},
                {"column_name": "BUS_CAPACITY"},
                {"column_name": "BUS_LICENSE_NUMBER"},
                {"column_name": "LAST_RENEW_LICI"},
                {"column_name": "NEXT_RENEW_LICI"},
                {"column_name": "EMP_ID_DESC"},
            ],
            [],
        ]
        get_transportation_buses()
        sql = query_all.call_args_list[1].args[0]
        self.assertIn("BUS_SCHOOL_ID", sql)
        self.assertIn("BUS_SCHOOL_NUMBER", sql)
        self.assertIn("AS oracle_bus_id", sql)
        self.assertIn("BUS_CAPACITY AS registered_capacity", sql)
        self.assertIn("BUS_LICENSE_NUMBER AS plate_number", sql)
        self.assertIn("LAST_RENEW_LICI AS last_license_renewal", sql)
        self.assertIn("EMP_ID_DESC AS driver_employee_name", sql)
        self.assertNotIn("|| ':' ||", sql)

    @patch("repositories.transportation_repo.query_all")
    def test_regions_use_bound_study_year(self, query_all):
        query_all.return_value = []
        get_transportation_regions("2026/2027")
        sql, binds = query_all.call_args.args
        self.assertIn("SCH_FAMILY_CARD", sql)
        self.assertIn("SCH_STUDENT_CARD_YEAR", sql)
        self.assertEqual(binds, {"study_year": "2026/2027"})


if __name__ == "__main__":
    unittest.main()

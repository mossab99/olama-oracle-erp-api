import unittest
from unittest.mock import patch

from app import create_app
from config import Config
from repositories.transportation_repo import get_transportation_students


class TransportationRouteTests(unittest.TestCase):
    def setUp(self):
        app = create_app()
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.headers = {"X-API-Key": Config.API_SECRET_KEY}

    def test_requires_api_key(self):
        self.assertEqual(
            self.client.get("/api/transportation/students").status_code, 401
        )

    def test_rejects_invalid_limit(self):
        response = self.client.get(
            "/api/transportation/students?limit=1001", headers=self.headers
        )
        self.assertEqual(response.status_code, 400)

    @patch("routes.transportation.get_transportation_student_count")
    @patch("routes.transportation.get_transportation_students")
    def test_student_contract(self, get_students, get_count):
        get_students.return_value = [{
            "student_id": 8,
            "family_id": 22,
            "legacy_morning_bus_id": 3,
        }]
        get_count.return_value = 1
        response = self.client.get(
            "/api/transportation/students?study_year=2026%2F2027"
            "&family_id=22&region_id=6&limit=20&offset=2",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["total"], 1)
        get_students.assert_called_once_with("2026/2027", 20, 2, 22, 6)

    @patch("routes.transportation.get_transportation_buses")
    def test_buses_contract(self, get_buses):
        get_buses.return_value = [{"oracle_bus_id": 1, "registered_capacity": 23}]
        response = self.client.get(
            "/api/transportation/buses?include_inactive=0",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        get_buses.assert_called_once_with(False)

    @patch("routes.transportation.get_transportation_employees")
    def test_employees_contract_uses_confirmed_references(self, get_employees):
        get_employees.return_value = [{
            "employee_id": 74, "employee_role": "driver"
        }]
        response = self.client.get(
            "/api/transportation/employees", headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["employees"][0]["employee_id"], 74)


class TransportationRepositoryTests(unittest.TestCase):
    @patch("repositories.transportation_repo.query_all")
    def test_student_query_is_read_only_and_paginated(self, query_all):
        query_all.return_value = []
        get_transportation_students("2026/2027", 20, 5, 22, 6)
        sql, params = query_all.call_args.args
        self.assertIn("SCH_STUDENT_TOT_TRANS", sql)
        self.assertIn("ROWNUM <= :max_row", sql)
        self.assertEqual(params["max_row"], 25)
        self.assertEqual(params["offset"], 5)
        for forbidden in (
            "INSERT ", "UPDATE ", "DELETE ", "MERGE ", "DROP ", "ALTER "
        ):
            self.assertNotIn(forbidden, sql.upper())


if __name__ == "__main__":
    unittest.main()

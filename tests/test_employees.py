import unittest
from datetime import date
from unittest.mock import patch

from app import create_app
from config import Config
from repositories.employees_repo import get_active_employees


EMPLOYEE_COLUMNS = [
    {"column_name": "EMP_ID", "data_type": "NUMBER"},
    {"column_name": "EMP_FULL_NAME", "data_type": "VARCHAR2"},
    {"column_name": "NATIONAL_NUMBER", "data_type": "VARCHAR2"},
    {"column_name": "BIRTH_DATE", "data_type": "DATE"},
    {"column_name": "EMP_GENDER", "data_type": "NUMBER"},
    {"column_name": "EMP_JOB_ID_DESC", "data_type": "VARCHAR2"},
    {"column_name": "EMP_APPOINTMENT", "data_type": "DATE"},
    {"column_name": "EMP_ADDRESS", "data_type": "VARCHAR2"},
    {"column_name": "EMP_PHONES", "data_type": "VARCHAR2"},
    {"column_name": "CERT_GRADE_ID_DESC", "data_type": "VARCHAR2"},
    {"column_name": "CERT_TYPE_DESC", "data_type": "VARCHAR2"},
    {"column_name": "CERT_DATE", "data_type": "DATE"},
    {"column_name": "CERT_AVERAGE", "data_type": "NUMBER"},
    {"column_name": "EMPLOYTE_CASE_DESC", "data_type": "VARCHAR2"},
]


class EmployeeRouteTests(unittest.TestCase):
    def setUp(self):
        app = create_app()
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.headers = {"X-API-Key": Config.API_SECRET_KEY}

    def test_requires_api_key(self):
        response = self.client.get("/api/employees")
        self.assertEqual(response.status_code, 401)

    @patch("routes.employees.get_active_employees")
    def test_returns_only_repository_results(self, get_employees):
        get_employees.return_value = [{
            "employee_id": 79,
            "full_name": "Test Employee",
            "employee_status": "مستمر",
        }]
        response = self.client.get(
            "/api/employees?limit=25&offset=5", headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["employee_status"], "مستمر")
        self.assertEqual(payload["count"], 1)
        get_employees.assert_called_once_with(limit=25, offset=5)

    def test_rejects_invalid_limit(self):
        response = self.client.get("/api/employees?limit=1001", headers=self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["message"], "Invalid limit")

    @patch("routes.employees.get_active_employees")
    def test_does_not_expose_repository_errors(self, get_employees):
        get_employees.side_effect = RuntimeError("sensitive Oracle detail")
        response = self.client.get("/api/employees", headers=self.headers)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("sensitive", response.get_data(as_text=True))


class EmployeeRepositoryTests(unittest.TestCase):
    @patch("repositories.employees_repo.query_all")
    def test_filters_exact_active_arabic_status_and_paginates(self, query_all):
        query_all.side_effect = [
            EMPLOYEE_COLUMNS,
            [{
                "employee_id": 79,
                "full_name": "Test Employee",
                "birth_date": date(1981, 7, 8),
                "employee_status": "مستمر",
                "rn": 3,
            }],
        ]
        rows = get_active_employees(limit=10, offset=2)
        sql, params = query_all.call_args.args
        self.assertIn("TRIM(e.EMPLOYTE_CASE_DESC) = :active_status", sql)
        self.assertIn("ROWNUM <= :max_row", sql)
        self.assertEqual(params["active_status"], "مستمر")
        self.assertEqual(params["max_row"], 12)
        self.assertEqual(params["offset"], 2)
        self.assertEqual(rows[0]["birth_date"], "1981-07-08")
        self.assertNotIn("rn", rows[0])

    @patch("repositories.employees_repo.query_all")
    def test_resolves_numeric_status_through_lookup_table(self, query_all):
        columns = [
            {"column_name": "EMP_ID", "data_type": "NUMBER"},
            {"column_name": "EMP_FULL_NAME", "data_type": "VARCHAR2"},
            {"column_name": "EMPLOYTE_CASE_ID", "data_type": "NUMBER"},
        ]
        lookup_columns = [
            {"table_name": "HR_EMPLOYTE_CASE", "column_name": "EMPLOYTE_CASE_ID"},
            {"table_name": "HR_EMPLOYTE_CASE", "column_name": "EMPLOYTE_CASE_DESC"},
        ]
        query_all.side_effect = [columns, lookup_columns, []]
        get_active_employees(limit=20, offset=0)
        sql, params = query_all.call_args.args
        self.assertIn("LEFT JOIN HR_EMPLOYTE_CASE employee_case", sql)
        self.assertIn("TRIM(employee_case.EMPLOYTE_CASE_DESC) = :active_status", sql)
        self.assertEqual(params["active_status"], "مستمر")


if __name__ == "__main__":
    unittest.main()

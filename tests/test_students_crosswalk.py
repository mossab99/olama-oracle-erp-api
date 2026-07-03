import unittest
from datetime import datetime
from unittest.mock import patch

from app import create_app
from config import Config
from repositories.students_crosswalk_repo import (
    get_student_crosswalk,
    get_student_crosswalk_diagnostics,
    get_student_crosswalk_schema_candidates,
)


FAKE_ROW = {
    "oracle_student_key": "459:3",
    "oracle_family_id": 459,
    "oracle_student_id": 3,
    "study_year": "2025/2026",
    "student_status": 1,
    "student_status_text": "ACTIVE",
    "class_id": 4,
    "class_name": "Grade 4",
    "section_id": 2,
    "section_name": "A",
    "school_id": 1,
    "school_name": "Main School",
    "branch_id": 1,
    "branch_name": "Main Branch",
    "registration_date": "2025-09-01",
    "withdraw_date": None,
    "immutable_legacy_billing_student_ref": None,
    "legacy_billing_student_id": None,
    "legacy_school_student_id": None,
}


class StudentCrosswalkRouteTests(unittest.TestCase):
    def setUp(self):
        app = create_app()
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.headers = {"X-API-Key": Config.API_SECRET_KEY}

    def test_requires_api_key(self):
        response = self.client.get("/api/students/crosswalk")
        self.assertEqual(response.status_code, 401)

    @patch("routes.students_crosswalk.get_student_crosswalk")
    def test_returns_non_pii_contract_and_filters(self, get_crosswalk):
        get_crosswalk.return_value = [FAKE_ROW]
        response = self.client.get(
            "/api/students/crosswalk"
            "?study_year=2025%2F2026&include_inactive=yes&limit=10&offset=2"
            "&family_id=459&student_id=3",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["filters"]["include_inactive"], 1)
        self.assertNotIn("student_name", payload["students"][0])
        self.assertNotIn("student_national_no", payload["students"][0])
        get_crosswalk.assert_called_once_with(
            study_year="2025/2026",
            include_inactive=True,
            family_id=459,
            student_id=3,
            limit=10,
            offset=2,
        )

    def test_rejects_invalid_limit(self):
        response = self.client.get(
            "/api/students/crosswalk?limit=2001", headers=self.headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["message"], "Invalid limit")

    @patch("routes.students_crosswalk.get_student_crosswalk_diagnostics")
    def test_diagnostics_are_counts_only(self, get_diagnostics):
        get_diagnostics.return_value = {
            "student_year_rows": 2,
            "unique_oracle_student_keys": 2,
            "duplicate_oracle_student_keys": 0,
        }
        response = self.client.get(
            "/api/students/crosswalk/diagnostics?study_year=2025%2F2026",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["diagnostics"]["student_year_rows"], 2)

    @patch("routes.students_crosswalk.get_student_crosswalk_schema_candidates")
    def test_schema_candidates_return_metadata_only(self, get_candidates):
        get_candidates.return_value = [{
            "table_name": "SCH_STUDENT_CARD",
            "column_name": "STUDENT_REF",
        }]
        response = self.client.get(
            "/api/students/crosswalk/schema-candidates", headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["count"], 1)


class StudentCrosswalkRepositoryTests(unittest.TestCase):
    @patch("repositories.students_crosswalk_repo.query_all")
    def test_crosswalk_uses_bound_filters_and_oracle_11g_pagination(self, query_all):
        query_all.return_value = [{
            "oracle_student_key": "459:3",
            "registration_date": datetime(2025, 9, 1),
            "withdraw_date": None,
            "rn": 8,
        }]
        rows = get_student_crosswalk(
            study_year="2025/2026",
            include_inactive=True,
            family_id=459,
            student_id=3,
            limit=5,
            offset=7,
        )
        sql, params = query_all.call_args.args
        self.assertIn("ROWNUM <= :max_row", sql)
        self.assertIn("WHERE rn > :offset", sql)
        self.assertIn("y.STUDY_YEAR = :study_year", sql)
        self.assertNotIn("y.STUDENT_STATUS = 1", sql)
        self.assertEqual(params["max_row"], 12)
        self.assertEqual(params["offset"], 7)
        self.assertEqual(params["family_id"], 459)
        self.assertEqual(rows[0]["registration_date"], "2025-09-01")
        self.assertNotIn("rn", rows[0])

        upper_sql = sql.upper()
        for keyword in (
            "INSERT", "UPDATE", "DELETE", "MERGE", "TRUNCATE",
            "DROP", "ALTER", "CREATE",
        ):
            self.assertNotIn(keyword, upper_sql)
        for forbidden in (
            "STUDENT_NAME", "STUDENT_NATIONAL_NO", "STUDENT_MOBILE",
            "FAMILY_ADDRESS", "FATHER_MOBILE", "MOTHER_MOBILE", "NOTES",
            "MOTHER_NAME",
        ):
            self.assertNotIn(forbidden, upper_sql)

    @patch("repositories.students_crosswalk_repo.query_one")
    def test_diagnostics_merge_count_queries(self, query_one):
        query_one.side_effect = [
            {"student_year_rows": 10, "unique_oracle_student_keys": 8},
            {"duplicate_oracle_student_keys": 1},
            {"student_id_values_reused_across_families": 2},
        ]
        result = get_student_crosswalk_diagnostics("2025/2026")
        self.assertEqual(result["student_year_rows"], 10)
        self.assertEqual(result["duplicate_oracle_student_keys"], 1)
        self.assertEqual(result["student_id_values_reused_across_families"], 2)
        for call in query_one.call_args_list:
            self.assertEqual(call.args[1]["study_year"], "2025/2026")

    @patch("repositories.students_crosswalk_repo.query_all")
    def test_schema_discovery_reads_known_metadata_only(self, query_all):
        query_all.return_value = []
        self.assertEqual(get_student_crosswalk_schema_candidates(), [])
        sql = query_all.call_args.args[0]
        self.assertIn("USER_TAB_COLUMNS", sql)
        self.assertIn("SCH_STUDENT_CARD", sql)
        self.assertIn("SCH_STUDENT_CARD_YEAR", sql)


if __name__ == "__main__":
    unittest.main()

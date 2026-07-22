import unittest
from unittest.mock import patch

from app import create_app
from config import Config
from repositories.academic_info_repo import (
    get_academic_students,
    get_grade_subjects,
)


class AcademicInfoRouteTests(unittest.TestCase):
    def setUp(self):
        app = create_app()
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.headers = {"X-API-Key": Config.API_SECRET_KEY}

    def test_requires_api_key(self):
        self.assertEqual(self.client.get("/api/academic/grades").status_code, 401)

    def test_requires_study_year(self):
        response = self.client.get(
            "/api/academic/grade-sections", headers=self.headers
        )
        self.assertEqual(response.status_code, 400)

    @patch("routes.academic_info.get_academic_students")
    def test_students_support_grade_and_section_filters(self, get_students):
        get_students.return_value = [{"student_id": 8, "grade_id": 4}]
        response = self.client.get(
            "/api/academic/students?study_year=2026-2027&grade_id=4&section_id=2",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["count"], 1)
        get_students.assert_called_once_with("2026-2027", 4, 2)

    @patch("routes.academic_info.get_academic_snapshot")
    def test_snapshot_contract(self, get_snapshot):
        get_snapshot.return_value = {
            "study_year": "2026-2027",
            "grades": [],
            "sections": [],
            "grade_sections": [],
            "students": [],
            "grade_subjects": [],
        }
        response = self.client.get(
            "/api/academic/snapshot?study_year=2026-2027", headers=self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")


class AcademicInfoRepositoryTests(unittest.TestCase):
    @patch("repositories.academic_info_repo.query_all")
    def test_student_query_uses_year_and_optional_filters(self, query_all):
        query_all.return_value = []
        get_academic_students("2026-2027", 4, 2)
        sql, params = query_all.call_args.args
        self.assertIn("SCH_STUDENT_CARD_YEAR", sql)
        self.assertIn("y.CLASS_ID = :grade_id", sql)
        self.assertIn("y.SECTION_ID = :section_id", sql)
        self.assertIn("y.STUDENT_STATUS = 1", sql)
        self.assertEqual(params["study_year"], "2026-2027")

    @patch("repositories.academic_info_repo.query_all")
    def test_subject_query_resolves_confirmed_source_from_metadata(self, query_all):
        query_all.side_effect = [
            [
                {"table_name": "SCH_MRK_CLS_SUBJECTS_M", "column_name": "STUDY_YEAR"},
                {"table_name": "SCH_MRK_CLS_SUBJECTS_M", "column_name": "CLASS_ID"},
                {"table_name": "SCH_MRK_CLS_SUBJECTS_M", "column_name": "SUBJECT_ID"},
                {"table_name": "SCH_MRK_CLS_SUBJECTS_M", "column_name": "SUBJECT_ID_DESC"},
                {"table_name": "SCH_MRK_CLS_SUBJECTS_M", "column_name": "IS_ACTIVE"},
            ],
            [],
        ]
        get_grade_subjects("2026-2027")
        sql, params = query_all.call_args_list[1].args
        self.assertIn("FROM SCH_MRK_CLS_SUBJECTS_M link", sql)
        self.assertIn("link.STUDY_YEAR = :study_year", sql)
        self.assertIn("link.SUBJECT_ID_DESC AS subject_name", sql)
        self.assertIn("NVL(link.IS_ACTIVE, 1) AS is_active", sql)
        self.assertIn("MAX(academic_rows.is_active) DESC", sql)
        self.assertIn("GROUP BY", sql)
        self.assertIn("academic_rows.grade_id", sql)
        self.assertIn("academic_rows.subject_id", sql)
        self.assertNotIn("NVL(link.IS_ACTIVE, 1) = 1", sql)
        self.assertEqual(params["study_year"], "2026-2027")

    @patch("repositories.academic_info_repo.query_all")
    def test_subject_query_supports_parent_grade_block(self, query_all):
        query_all.side_effect = [
            [
                {"table_name": "SCH_MRK_AVE_PARAM", "column_name": "LAW_ID"},
                {"table_name": "SCH_MRK_AVE_PARAM", "column_name": "CLASS_ID"},
                {"table_name": "SCH_MRK_CLS_SUBJECTS_M", "column_name": "LAW_ID"},
                {"table_name": "SCH_MRK_CLS_SUBJECTS_M", "column_name": "SUBJECT_ID"},
                {"table_name": "SCH_SUBJECTS", "column_name": "SUBJECT_ID"},
                {"table_name": "SCH_SUBJECTS", "column_name": "SUBJECT_DESC"},
            ],
            [],
        ]
        get_grade_subjects("2026-2027")
        sql, params = query_all.call_args_list[1].args
        self.assertIn("JOIN SCH_MRK_AVE_PARAM grade_param", sql)
        self.assertIn("grade_param.LAW_ID = link.LAW_ID", sql)
        self.assertIn("grade_param.CLASS_ID AS grade_id", sql)
        self.assertIn("LEFT JOIN SCH_SUBJECTS subject", sql)
        self.assertEqual(params["study_year"], "2026-2027")


if __name__ == "__main__":
    unittest.main()

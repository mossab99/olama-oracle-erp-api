import re
import unittest
from datetime import date
from unittest.mock import patch

from app import create_app
from config import Config
from repositories.financial_contract_repo import (
    get_family_dues,
    get_family_receipts,
    get_family_transactions,
)


SUMMARY = {
    "status": "ok",
    "family_id": 459,
    "study_year": "2025/2026",
    "financial_available": True,
    "summary": {"balance": 10, "currency": "JOD"},
    "students": [{
        "oracle_family_id": 459,
        "oracle_student_id": 3,
        "oracle_student_key": "459:3",
    }],
    "source": {"oracle_tables": ["SCH_FIN_FAMILY_CARD"]},
}


class FinancialContractRouteTests(unittest.TestCase):
    def setUp(self):
        app = create_app()
        app.config.update(TESTING=True)
        self.client = app.test_client()
        self.headers = {"X-API-Key": Config.API_SECRET_KEY}

    def test_endpoints_require_api_key(self):
        paths = (
            "/api/financial/diagnostics",
            "/api/families/459/financial",
            "/api/families/459/financial-transactions",
            "/api/families/459/dues",
            "/api/families/459/receipts",
            "/api/families/459/payments",
            "/api/students/459:3/financial-summary",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)

    def test_invalid_student_key_returns_400(self):
        response = self.client.get(
            "/api/students/3/financial-summary", headers=self.headers
        )
        self.assertEqual(response.status_code, 400)

    @patch("routes.financial_contract.get_student_financial_summary")
    def test_valid_student_key_is_parsed_as_composite(self, get_summary):
        get_summary.return_value = {
            "status": "ok",
            "oracle_family_id": 459,
            "oracle_student_id": 3,
            "oracle_student_key": "459:3",
        }
        response = self.client.get(
            "/api/students/459:3/financial-summary?study_year=2025%2F2026",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        get_summary.assert_called_once_with(459, 3, "2025/2026")

    @patch("routes.financial_contract.get_family_summary_contract")
    def test_family_summary_alias_is_pii_free(self, get_summary):
        get_summary.return_value = SUMMARY
        response = self.client.get(
            "/api/families/459/financial?study_year=2025%2F2026",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        payload_text = response.get_data(as_text=True).lower()
        for field in (
            "student_name", "father_name", "mother_name", "phone",
            "mobile", "email", "address", "national_no", "notes",
        ):
            self.assertNotIn(f'"{field}"', payload_text)

    @patch("routes.messaging_financial.get_family_summary_contract")
    @patch("routes.messaging_financial.get_single_family_financial_summary")
    def test_existing_summary_shape_is_preserved_additively(
        self, get_legacy_summary, get_contract
    ):
        get_legacy_summary.return_value = {
            "family_id": 459,
            "study_year": "2025/2026",
            "balance": 10,
            "monthly_due": 5,
            "financial_available": True,
        }
        get_contract.return_value = SUMMARY
        response = self.client.get(
            "/api/families/459/financial-summary?study_year=2025%2F2026",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["balance"], 10)
        self.assertEqual(payload["monthly_due"], 5)
        self.assertIn("summary", payload)

    @patch("routes.financial_contract.get_family_transactions")
    def test_pagination_is_accepted(self, get_transactions):
        get_transactions.return_value = []
        response = self.client.get(
            "/api/families/459/transactions"
            "?study_year=2025%2F2026&limit=5&offset=2",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["limit"], 5)
        self.assertEqual(response.get_json()["offset"], 2)
        get_transactions.assert_called_once_with(459, "2025/2026", 5, 2)

    @patch("routes.financial_contract.get_financial_diagnostics")
    def test_diagnostics_are_counts_only(self, get_diagnostics):
        get_diagnostics.return_value = {
            "families_with_financial_rows": 1,
            "students_with_financial_rows": 2,
            "transaction_rows": 3,
            "due_rows": 4,
            "receipt_rows": 1,
            "rows_missing_family_id": 0,
            "rows_missing_student_id": 0,
            "rows_missing_stable_key": 0,
            "duplicate_serial_ids": 0,
            "duplicate_receipt_ids": 0,
            "student_id_values_reused_across_families": 0,
        }
        response = self.client.get(
            "/api/financial/diagnostics?study_year=2025%2F2026",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["diagnostics"]["transaction_rows"], 3)


class FinancialContractRepositoryTests(unittest.TestCase):
    @patch("repositories.financial_contract_repo.query_all")
    def test_transactions_use_oracle_11g_pagination_and_binds(self, query_all):
        query_all.return_value = [{
            "serial_id": 123,
            "receipt_id": None,
            "family_id": 459,
            "student_id": 3,
            "study_year": "2025/2026",
            "trans_date": date(2025, 9, 1),
            "title_id": 1,
            "title_type": 2,
            "trans_status": 1,
            "debit_amount": 100,
            "credit_amount": 0,
            "receipt_count": 0,
            "serial_count": 1,
            "rn": 8,
        }]
        rows = get_family_transactions(459, "2025/2026", 5, 7)
        sql, params = query_all.call_args.args
        self.assertIn("ROWNUM <= :max_row", sql)
        self.assertIn("WHERE rn > :offset", sql)
        self.assertIn("fs.FAMILY_ID = :family_id", sql)
        self.assertIsNone(re.search(r"\bOFFSET\s+[0-9]", sql, re.I))
        self.assertEqual(params["max_row"], 12)
        self.assertEqual(params["offset"], 7)
        self.assertEqual(rows[0]["oracle_student_key"], "459:3")
        self.assertEqual(rows[0]["oracle_transaction_key"], "serial:123")
        self.assertNotIn("student_name", rows[0])
        self._assert_select_only_and_short_aliases(sql)

    @patch("repositories.financial_contract_repo.query_all")
    def test_family_level_transaction_is_import_ready(self, query_all):
        query_all.return_value = [{
            "serial_id": 124,
            "receipt_id": None,
            "family_id": 459,
            "student_id": None,
            "study_year": "2025/2026",
            "trans_date": date(2025, 9, 2),
            "title_id": 1,
            "title_type": 2,
            "trans_status": 1,
            "debit_amount": 25,
            "credit_amount": 0,
            "receipt_count": 0,
            "serial_count": 1,
        }]
        row = get_family_transactions(459, "2025/2026", 5, 0)[0]
        self.assertIsNone(row["oracle_student_id"])
        self.assertIsNone(row["oracle_student_key"])
        self.assertEqual(row["identity_scope"], "family")
        self.assertEqual(row["import_readiness"], "IMPORT_READY")
        self.assertEqual(row["missing_requirements"], [])

    @patch("repositories.financial_contract_repo.query_all")
    def test_dues_are_not_ready_without_proven_stable_key(self, query_all):
        query_all.return_value = [{
            "family_id": 459,
            "study_year": "2025/2026",
            "due_date": date(2025, 9, 1),
            "due_amount": 100,
            "paid_amount": 40,
            "receipt_paid": 0,
        }]
        rows = get_family_dues(459, "2025/2026", 5, 0)
        self.assertIsNone(rows[0]["oracle_due_key"])
        self.assertEqual(rows[0]["import_readiness"], "NOT_IMPORT_READY")
        self.assertIn("stable_key", rows[0]["missing_requirements"])
        self._assert_select_only_and_short_aliases(query_all.call_args.args[0])

    @patch("repositories.financial_contract_repo.query_all")
    def test_receipts_are_aggregated_and_pii_free(self, query_all):
        query_all.return_value = [{
            "receipt_id": 777,
            "serial_id": 123,
            "family_id": 459,
            "student_id": 3,
            "study_year": "2025/2026",
            "receipt_date": date(2025, 10, 1),
            "receipt_amount": 50,
            "trans_status": 1,
            "line_count": 1,
        }]
        rows = get_family_receipts(459, "2025/2026", 5, 0)
        self.assertEqual(rows[0]["oracle_receipt_key"], "receipt:777")
        self.assertEqual(rows[0]["oracle_student_key"], "459:3")
        self.assertNotIn("notes", rows[0])
        self._assert_select_only_and_short_aliases(query_all.call_args.args[0])

    @patch("repositories.financial_contract_repo.query_all")
    def test_family_level_receipt_has_nullable_student_identity(self, query_all):
        query_all.return_value = [{
            "receipt_id": 778,
            "serial_id": 124,
            "family_id": 459,
            "student_id": None,
            "study_year": "2025/2026",
            "receipt_date": date(2025, 10, 2),
            "receipt_amount": 50,
            "trans_status": 1,
            "line_count": 2,
        }]
        row = get_family_receipts(459, "2025/2026", 5, 0)[0]
        self.assertIsNone(row["oracle_student_id"])
        self.assertIsNone(row["oracle_student_key"])
        self.assertEqual(row["identity_scope"], "family")
        self.assertEqual(row["import_readiness"], "IMPORT_READY")

    def _assert_select_only_and_short_aliases(self, sql):
        upper_sql = sql.upper()
        for keyword in (
            "INSERT", "UPDATE", "DELETE", "MERGE", "TRUNCATE",
            "DROP", "ALTER", "CREATE",
        ):
            self.assertNotIn(keyword, upper_sql)
        aliases = re.findall(r"\bAS\s+([A-Za-z][A-Za-z0-9_]*)", sql, re.I)
        self.assertTrue(aliases)
        self.assertTrue(all(len(alias) <= 30 for alias in aliases))


if __name__ == "__main__":
    unittest.main()

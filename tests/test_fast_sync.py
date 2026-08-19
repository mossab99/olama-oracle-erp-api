import unittest
from unittest.mock import patch

from app import create_app
from config import Config
from repositories.fast_sync_repo import get_fast_sync_page


class FastSyncRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()
        self.headers = {"X-API-Key": Config.API_SECRET_KEY}

    def test_requires_authentication(self):
        self.assertEqual(self.client.get("/api/v1/sync/families-bulk").status_code, 401)

    def test_rejects_invalid_pagination(self):
        response = self.client.get(
            "/api/v1/sync/families-bulk?limit=101", headers=self.headers
        )
        self.assertEqual(response.status_code, 400)

    @patch("routes.fast_sync.get_fast_sync_page")
    def test_returns_versioned_cursor_page(self, get_page):
        get_page.return_value = {
            "families": [{"family": {"family_id": 10}, "students": []}],
            "total": 12,
            "next_cursor": 10,
            "has_more": True,
        }
        response = self.client.get(
            "/api/v1/sync/families-bulk?study_year=2026%2F2027&limit=10&cursor=2",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["version"], 1)
        self.assertEqual(response.get_json()["next_cursor"], 10)
        get_page.assert_called_once_with("2026/2027", 10, 2)


class FastSyncRepositoryTests(unittest.TestCase):
    @patch("repositories.fast_sync_repo.query_one")
    @patch("repositories.fast_sync_repo.query_all")
    def test_groups_bulk_rows_into_family_bundles(self, query_all, query_one):
        query_one.return_value = {"total": 2}
        query_all.side_effect = [
            [{"family_id": 10}, {"family_id": 20}],
            [{"family_id": 10, "student_id": 1}],
            [{"family_id": 10, "balance": 5}],
            [{"family_id": 20, "due_amount": 7}],
            [{"family_id": 10, "serial_id": 9}],
            [{"family_id": 20, "student_id": 2}],
        ]

        page = get_fast_sync_page("2026/2027", 2, 0)

        self.assertEqual(page["next_cursor"], 20)
        self.assertTrue(page["has_more"])
        self.assertEqual(page["families"][0]["students"][0]["student_id"], 1)
        self.assertEqual(
            page["families"][0]["financial"]["student_transactions"][0]["serial_id"],
            9,
        )
        self.assertEqual(page["families"][1]["transportation"][0]["student_id"], 2)
        self.assertEqual(query_all.call_count, 6)


if __name__ == "__main__":
    unittest.main()
